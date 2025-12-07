import streamlit as st
import pandas as pd
import io

# Sayfa Ayarları
st.set_page_config(page_title="Sendika Listesi Düzenleyici", page_icon="📂")

st.title("📂 Sendika Listesi Düzenleyici")
st.write("Excel (.xls, .xlsx) veya CSV dosyanızı yükleyin, temizlenmiş halini indirin.")

# Dosya Yükleme Alanı
uploaded_file = st.file_uploader("Dosyayı buraya sürükleyin", type=["xls", "xlsx", "csv"])

def temizle_ve_donustur(file):
    df = None
    hata_mesaji = ""

    # Dosya uzantısını kontrol et
    file_name = file.name.lower()
    
    # --- OKUMA MANTIĞI ---
    try:
        if file_name.endswith('.xlsx'):
            df = pd.read_excel(file, header=None, engine='openpyxl')
        elif file_name.endswith('.xls'):
            try:
                df = pd.read_excel(file, header=None, engine='xlrd')
            except:
                # Bazen .xls uzantılı ama içi HTML/XML olabilir
                try:
                    dfs = pd.read_html(file)
                    if dfs: df = dfs[0]
                except:
                    pass
        
        # Eğer yukarıdakiler çalışmadıysa veya dosya CSV ise Text olarak dene
        if df is None:
            # BytesIO kullandığımız için pointer'ı başa almalıyız
            file.seek(0)
            encodings = ['utf-8', 'cp1254', 'latin1', 'iso-8859-9']
            for encoding in encodings:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, header=None, encoding=encoding, sep=None, engine='python')
                    break
                except:
                    continue

        if df is None:
            return None, "Dosya okunamadı. Format bozuk veya desteklenmiyor."

        # --- VERİ İŞLEME ---
        # Sütun İndeksleri: [2, 6, 13, 17, 26, 33] -> Sıra, ÜyeNo, Ad, Soyad, TC, Aidat
        if df.shape[1] < 34:
             return None, f"Dosya formatı hatalı. Sütun sayısı eksik ({df.shape[1]})."

        df_subset = df.iloc[:, [2, 6, 13, 17, 26, 33]].copy()
        df_subset.columns = ['Sira No', 'Uye No', 'Adi', 'Soyadi', 'TC Kimlik No', 'Aidat Tutari']

        # Filtreleme (Sıra No sayısal olmalı)
        df_subset['Kontrol'] = pd.to_numeric(df_subset['Sira No'], errors='coerce')
        df_clean = df_subset.dropna(subset=['Kontrol']).drop(columns=['Kontrol'])

        # Para Formatı
        def temizle_para(x):
            if pd.isna(x): return 0.0
            x = str(x).replace('TL', '').replace(' ', '')
            if ',' in x and '.' in x: x = x.replace('.', '') 
            x = x.replace(',', '.')
            try: return float(x)
            except: return 0.0
        
        df_clean['Aidat Tutari'] = df_clean['Aidat Tutari'].apply(temizle_para)

        # TC Kimlik
        df_clean['TC Kimlik No'] = df_clean['TC Kimlik No'].astype(str).str.split('.').str[0]
        df_clean.reset_index(drop=True, inplace=True)

        return df_clean, None

    except Exception as e:
        return None, str(e)

# Dosya yüklendiğinde çalışacak kısım
if uploaded_file is not None:
    with st.spinner('Dosya işleniyor...'):
        df_sonuc, hata = temizle_ve_donustur(uploaded_file)
        
        if hata:
            st.error(f"Hata: {hata}")
        elif df_sonuc is not None:
            st.success(f"İşlem Başarılı! Toplam {len(df_sonuc)} kayıt bulundu.")
            
            # Önizleme göster
            st.dataframe(df_sonuc.head())

            # İndirme Butonu Hazırlama
            # Pandas DF -> Excel Bytes
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_sonuc.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Düzenlenmiş Excel'i İndir",
                data=buffer.getvalue(),
                file_name="Duzenlenmis_Liste.xlsx",
                mime="application/vnd.ms-excel"
            )