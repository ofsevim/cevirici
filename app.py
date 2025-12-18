import streamlit as st
import pandas as pd
import re
import io

# -----------------------------------------------------------------------------
# 1. SAYFA AYARLARI
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Veri Temizleyici", layout="wide")

st.title("📂 Sendika Kesinti Listesi Düzenleyici")
st.markdown("""
Bu araç, karmaşık CSV/Excel çıktılarını temizler. 
Kolon eşleştirmesi otomatik yapılır, isterseniz manuel düzenleyebilirsiniz.
""")

# -----------------------------------------------------------------------------
# YARDIMCI FONKSİYON: BOZUK KARAKTERLERİ DÜZELT
# -----------------------------------------------------------------------------
def fix_turkish_chars(text):
    """
    Eğer metin bozuk gelirse (Örn: 'Ã¼' yerine 'ü', 'Ý' yerine 'İ') bunları düzeltir.
    """
    if not isinstance(text, str):
        return text
    
    # Yaygın encoding hataları haritası
    replacements = {
        'Ã¼': 'ü', 'Ã¶': 'ö', 'Ã§': 'ç', 'ÅŸ': 'ş', 'Ä±': 'ı', 'ÄŸ': 'ğ',
        'Ãœ': 'Ü', 'Ã–': 'Ö', 'Ã‡': 'Ç', 'Åž': 'Ş', 'Ä°': 'İ', 'Äž': 'Ğ',
        'Ý': 'İ', 'Þ': 'Ş', 'ð': 'ğ', 'ý': 'ı', 'þ': 'ş', 'Ð': 'Ğ'
    }
    
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text

# -----------------------------------------------------------------------------
# YARDIMCI FONKSİYON: OTOMATİK KOLON TESPİTİ
# -----------------------------------------------------------------------------
def auto_detect_columns(df):
    """
    DataFrame'deki kolonları otomatik olarak eşleştirir.
    Returns: dictionary with detected column mappings
    """
    mapping = {
        'uye_no': None,
        'adi': None,
        'soyadi': None,
        'tc_no': None,
        'tutar': None
    }
    
    columns_lower = [str(col).lower() for col in df.columns]
    
    for idx, col in enumerate(columns_lower):
        col_clean = fix_turkish_chars(col).strip()
        
        # TC Kimlik No tespiti
        if any(keyword in col_clean for keyword in ['tc', 'kimlik', 't.c', 'tcno', 'tckimlik']):
            mapping['tc_no'] = df.columns[idx]
        
        # Adı Soyadı (birleşik) tespiti - hem adı hem soyadı için kullan
        elif 'adı' in col_clean and 'soyad' in col_clean:
            # Birleşik kolon - ikisi için de kullan
            mapping['adi'] = df.columns[idx]
            mapping['soyadi'] = df.columns[idx]
        
        # Ad tespiti (ayrı kolon)
        elif any(keyword in col_clean for keyword in ['adı', 'adi', 'ad ', 'isim', 'name']) and 'soyad' not in col_clean:
            mapping['adi'] = df.columns[idx]
        
        # Soyad tespiti (ayrı kolon)
        elif any(keyword in col_clean for keyword in ['soyad', 'soyadı', 'surname']):
            mapping['soyadi'] = df.columns[idx]
        
        # Üye No / Sıra No tespiti
        elif any(keyword in col_clean for keyword in ['üye', 'uye', 'sıra', 'sira', 'sicil', 'member', 'persone']):
            if mapping['uye_no'] is None:  # İlk bulunan
                mapping['uye_no'] = df.columns[idx]
        
        # Tutar tespiti
        elif any(keyword in col_clean for keyword in ['tutar', 'aidat', 'miktar', 'amount', 'ücret', 'ucret']):
            mapping['tutar'] = df.columns[idx]
    
    return mapping

# -----------------------------------------------------------------------------
# YARDIMCI FONKSİYON: TC NO İLE KOLON TESPİTİ (Fallback)
# -----------------------------------------------------------------------------
def detect_columns_by_tc(df):
    """
    Eğer başlık satırı yoksa, TC numarasını bulup göreceli pozisyondan kolonları tahmin eder.
    """
    mapping = {
        'uye_no': None,
        'adi': None,
        'soyadi': None,
        'tc_no': None,
        'tutar': None
    }
    
    # İlk satırda TC ara
    first_row = df.iloc[0] if len(df) > 0 else None
    if first_row is None:
        return mapping
    
    tc_col_idx = None
    for idx, val in enumerate(first_row):
        if pd.notna(val) and re.match(r'^\d{11}$', str(val).strip()):
            tc_col_idx = idx
            break
    
    if tc_col_idx is not None:
        mapping['tc_no'] = df.columns[tc_col_idx]
        
        # Göreceli pozisyonlar
        if tc_col_idx > 0:
            mapping['soyadi'] = df.columns[tc_col_idx - 1]
        if tc_col_idx > 1:
            mapping['adi'] = df.columns[tc_col_idx - 2]
        if tc_col_idx > 2:
            mapping['uye_no'] = df.columns[tc_col_idx - 3]
        if tc_col_idx < len(df.columns) - 1:
            mapping['tutar'] = df.columns[tc_col_idx + 1]
    
    return mapping

# -----------------------------------------------------------------------------
# 2. VERİ TEMİZLEME FONKSİYONU (MAPPING İLE)
# -----------------------------------------------------------------------------
def clean_data_with_mapping(df, column_mapping):
    """
    Kullanıcının belirlediği mapping'e göre veriyi temizler.
    """
    data_rows = []
    
    for idx, row in df.iterrows():
        try:
            # Mapping'den kolonları al
            uye_no = str(row[column_mapping['uye_no']]) if column_mapping['uye_no'] and pd.notna(row.get(column_mapping['uye_no'])) else ""
            tc_no = str(row[column_mapping['tc_no']]) if column_mapping['tc_no'] and pd.notna(row.get(column_mapping['tc_no'])) else ""
            tutar = str(row[column_mapping['tutar']]) if column_mapping['tutar'] and pd.notna(row.get(column_mapping['tutar'])) else "0"
            
            # Ad ve Soyad - birleşik veya ayrı olabilir
            if column_mapping['adi'] == column_mapping['soyadi'] and column_mapping['adi']:
                # Birleşik kolon (Adı Soyadı)
                full_name = str(row[column_mapping['adi']]) if pd.notna(row.get(column_mapping['adi'])) else ""
                full_name = fix_turkish_chars(full_name).strip()
                
                # İsmi ayır (ilk kelime ad, geri kalanı soyad)
                name_parts = full_name.split(maxsplit=1)
                adi = name_parts[0] if len(name_parts) > 0 else ""
                soyadi = name_parts[1] if len(name_parts) > 1 else ""
            else:
                # Ayrı kolonlar
                adi = str(row[column_mapping['adi']]) if column_mapping['adi'] and pd.notna(row.get(column_mapping['adi'])) else ""
                soyadi = str(row[column_mapping['soyadi']]) if column_mapping['soyadi'] and pd.notna(row.get(column_mapping['soyadi'])) else ""
                
                # Türkçe karakter düzeltmeleri
                adi = fix_turkish_chars(adi).strip()
                soyadi = fix_turkish_chars(soyadi).strip()
            
            # TC No temizle (sadece rakamlar)
            tc_no = re.sub(r'\D', '', tc_no)
            
            # TC No kontrolü (11 hane olmalı)
            if len(tc_no) != 11:
                continue
            
            # Tutar temizle
            tutar = tutar.replace('"', '').replace("'", "").replace(',', '.')
            # Fazladan boşlukları temizle
            tutar = tutar.strip()
            
            row_dict = {
                "Üye No": uye_no.strip(),
                "Adı": adi,
                "Soyadı": soyadi,
                "TC Kimlik No": tc_no,
                "Aidat Tutarı": tutar
            }
            data_rows.append(row_dict)
            
        except Exception as e:
            continue
    
    # DataFrame oluştur
    df_clean = pd.DataFrame(data_rows)
    
    # Tutarı sayıya çevir
    try:
        df_clean["Aidat Tutarı"] = pd.to_numeric(df_clean["Aidat Tutarı"], errors='coerce').fillna(0)
    except:
        pass
    
    return df_clean

# -----------------------------------------------------------------------------
# 3. ARAYÜZ VE DOSYA YÜKLEME
# -----------------------------------------------------------------------------
uploaded_file = st.file_uploader("Dosyayı Yükle", type=["csv", "xlsx", "txt", "xls"])

if uploaded_file is not None:
    st.info("Dosya yükleniyor...")
    
    try:
        df_raw = None
        
        # Excel Okuma
        if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            try:
                # Önce tüm veriyi header=None ile oku
                df_all = pd.read_excel(uploaded_file, header=None, dtype=str)
                
                # Başlık satırını bul (TC Kimlik, Adı, Soyadı gibi içeren satır)
                header_row_idx = None
                for idx, row in df_all.iterrows():
                    row_str = ' '.join([str(x).lower() for x in row if pd.notna(x)])
                    # TC Kimlik içeren satırı bul
                    if 'tc' in row_str or 'kimlik' in row_str or 'ad' in row_str and 'soyad' in row_str:
                        header_row_idx = idx
                        break
                
                if header_row_idx is not None:
                    # Başlık satırından itibaren oku
                    uploaded_file.seek(0)
                    df_raw = pd.read_excel(uploaded_file, header=header_row_idx, dtype=str)
                    
                    # Boş satırları temizle
                    df_raw = df_raw.dropna(how='all')
                    
                    # Kolon isimlerini temizle (merged cells'den gelen sorunlar için)
                    new_cols = []
                    for col in df_raw.columns:
                        col_str = str(col).strip()
                        # "Unnamed" kolonları temizle
                        if 'Unnamed' not in col_str and col_str != 'nan':
                            new_cols.append(col_str)
                        else:
                            new_cols.append(col_str)
                    df_raw.columns = new_cols
                    
                    # TC olan ilk satırı bul (veri başlangıcı)
                    first_data_idx = None
                    for idx, row in df_raw.iterrows():
                        for val in row:
                            if pd.notna(val) and re.search(r'\d{11}', str(val)):
                                first_data_idx = idx
                                break
                        if first_data_idx is not None:
                            break
                    
                    if first_data_idx is not None:
                        df_raw = df_raw.loc[first_data_idx:].reset_index(drop=True)
                else:
                    # Başlık bulunamadı, normal okuma
                    uploaded_file.seek(0)
                    df_raw = pd.read_excel(uploaded_file, dtype=str)
                    
            except Exception as excel_error:
                st.error(f"Excel okuma hatası: {excel_error}")
                st.exception(excel_error)
                st.stop()
        
        # CSV/TXT Okuma (Encoding Denemeleri)
        else:
            raw_bytes = uploaded_file.getvalue()
            string_data = None
            
            # Encoding denemeleri
            for encoding in ['cp1254', 'utf-8', 'iso-8859-9', 'latin-1']:
                try:
                    string_data = raw_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if string_data is None:
                st.error("Dosya encoding'i algılanamadı.")
                st.stop()
            
            # Ayırıcıyı tespit et
            delimiter = ';' if ';' in string_data.split('\n')[0] else ','
            
            # DataFrame'e çevir
            try:
                df_raw = pd.read_csv(io.StringIO(string_data), sep=delimiter, dtype=str)
                
                # Eğer başlık yoksa
                if df_raw.columns[0] and re.match(r'^\d+$', str(df_raw.columns[0])):
                    df_raw = pd.read_csv(io.StringIO(string_data), sep=delimiter, header=None, dtype=str)
            except:
                df_raw = pd.read_csv(io.StringIO(string_data), sep=delimiter, header=None, dtype=str)
        
        # DataFrame yüklendi
        if df_raw is not None and not df_raw.empty:
            st.success(f"✅ Dosya başarıyla yüklendi! Toplam {len(df_raw)} satır bulundu.")
            
            # Önizleme
            st.subheader("📋 Veri Önizleme (İlk 5 Satır)")
            st.dataframe(df_raw.head(), use_container_width=True)
            
            # Kolon sayısı uyarısı
            if len(df_raw.columns) < 3:
                st.warning("⚠️ Az sayıda kolon tespit edildi. Eğer veriler düzgün görünmüyorsa, Excel'deki merged cell'leri kaldırın.")
            
            # Otomatik kolon tespiti
            auto_mapping = auto_detect_columns(df_raw)
            
            # Eğer otomatik tespit başarısızsa, TC bazlı tespit dene
            if auto_mapping['tc_no'] is None:
                auto_mapping = detect_columns_by_tc(df_raw)
            
            # Kolon Eşleştirme Arayüzü
            st.subheader("🔗 Kolon Eşleştirme")
            st.markdown("Aşağıdan her bir hedef alana karşılık gelen kaynak kolonu seçin:")
            
            col1, col2, col3 = st.columns(3)
            
            available_columns = ['(Boş)'] + list(df_raw.columns)
            
            with col1:
                uye_no_col = st.selectbox(
                    "Üye No",
                    options=available_columns,
                    index=available_columns.index(auto_mapping['uye_no']) if auto_mapping['uye_no'] in available_columns else 0
                )
                
                tc_no_col = st.selectbox(
                    "TC Kimlik No ⚠️ (Zorunlu)",
                    options=available_columns,
                    index=available_columns.index(auto_mapping['tc_no']) if auto_mapping['tc_no'] in available_columns else 0
                )
            
            with col2:
                adi_col = st.selectbox(
                    "Adı",
                    options=available_columns,
                    index=available_columns.index(auto_mapping['adi']) if auto_mapping['adi'] in available_columns else 0
                )
                
                tutar_col = st.selectbox(
                    "Aidat Tutarı",
                    options=available_columns,
                    index=available_columns.index(auto_mapping['tutar']) if auto_mapping['tutar'] in available_columns else 0
                )
            
            with col3:
                soyadi_col = st.selectbox(
                    "Soyadı",
                    options=available_columns,
                    index=available_columns.index(auto_mapping['soyadi']) if auto_mapping['soyadi'] in available_columns else 0
                )
            
            # Mapping oluştur
            column_mapping = {
                'uye_no': None if uye_no_col == '(Boş)' else uye_no_col,
                'adi': None if adi_col == '(Boş)' else adi_col,
                'soyadi': None if soyadi_col == '(Boş)' else soyadi_col,
                'tc_no': None if tc_no_col == '(Boş)' else tc_no_col,
                'tutar': None if tutar_col == '(Boş)' else tutar_col
            }
            
            # İşleme butonu
            if st.button("🚀 Veriyi İşle", type="primary", use_container_width=True):
                if column_mapping['tc_no'] is None:
                    st.error("❌ TC Kimlik No kolonu seçilmesi zorunludur!")
                else:
                    with st.spinner("Veriler işleniyor..."):
                        df_clean = clean_data_with_mapping(df_raw, column_mapping)
                        
                        if not df_clean.empty:
                            st.success(f"✅ Başarılı! Toplam {len(df_clean)} kişi listelendi.")
                            
                            # Temiz veriyi göster
                            st.subheader("📊 Temizlenmiş Veri")
                            st.dataframe(df_clean, use_container_width=True)
                            
                            # Excel İndir
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                df_clean.to_excel(writer, index=False, sheet_name='Temiz Liste')
                                workbook = writer.book
                                worksheet = writer.sheets['Temiz Liste']
                                
                                # Başlık Formatı (Kalın ve Renkli)
                                header_format = workbook.add_format({
                                    'bold': True,
                                    'text_wrap': True,
                                    'valign': 'top',
                                    'fg_color': '#D7E4BC',
                                    'border': 1
                                })
                                
                                for col_num, value in enumerate(df_clean.columns.values):
                                    worksheet.write(0, col_num, value, header_format)
                                    
                                worksheet.set_column('A:E', 20)
                            
                            st.download_button(
                                label="📥 Temiz Excel İndir",
                                data=buffer.getvalue(),
                                file_name="BMS_Sendika_Temiz.xlsx",
                                mime="application/vnd.ms-excel",
                                use_container_width=True
                            )
                        else:
                            st.warning("⚠️ Geçerli TC Kimlik No bulunamadı. Lütfen kolon eşleştirmesini kontrol edin.")
        else:
            st.error("Dosya okunamadı veya boş.")
                
    except Exception as e:
        st.error(f"❌ Beklenmeyen hata: {e}")
        st.exception(e)