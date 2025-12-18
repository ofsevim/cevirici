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
Bu araç, karmaşık CSV/Excel çıktılarını temizler ve düzenler.
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
# 2. HAM VERİ PARSE FONKSİYONU (Tüm kolonları çıkar)
# -----------------------------------------------------------------------------
def parse_raw_data(file_content):
    """
    Ham veriyi parse eder ve TC Kimlik içeren satırları bulur.
    Her satırı kolonlara ayırır.
    """
    data_rows = []
    lines = file_content.splitlines()
    
    for line in lines:
        # TC Kimlik bul (11 hane)
        tc_match = re.search(r'(?<!\d)\d{11}(?!\d)', line)
        
        if tc_match:
            # Ayırıcıyı belirle (Noktalı virgül öncelikli)
            if ";" in line:
                parts = line.split(';')
            else:
                parts = line.split(',')
            
            # Temizle
            clean_parts = [p.strip() for p in parts if p.strip()]
            
            # Türkçe karakterleri düzelt
            clean_parts = [fix_turkish_chars(p) for p in clean_parts]
            
            if len(clean_parts) >= 3:  # En az 3 kolon olmalı
                data_rows.append(clean_parts)
    
    return data_rows

# -----------------------------------------------------------------------------
# 3. VERİ TEMİZLEME FONKSİYONU (Kolon haritası ile)
# -----------------------------------------------------------------------------
def clean_data_with_mapping(raw_data, column_mapping, id_column_name, same_column=False):
    """
    Args:
        raw_data: Ham veri satırları (liste)
        column_mapping: Kolon indekslerinin haritası
        id_column_name: ID kolonu adı (Üye No / Personel No)
        same_column: Ad ve Soyad aynı kolonda mı?
    """
    cleaned_rows = []
    
    for row in raw_data:
        try:
            # TC Kimlik bul
            tc_value = None
            for item in row:
                if re.match(r'^\d{11}$', str(item)):
                    tc_value = item
                    break
            
            if not tc_value:
                continue
            
            # ID No
            id_no = row[column_mapping['id_no']] if column_mapping['id_no'] < len(row) else ""
            
            # Ad-Soyad aynı kolonda mı?
            if same_column:
                full_name = row[column_mapping['adi']] if column_mapping['adi'] < len(row) else ""
                full_name = str(full_name).strip()
                
                # Boşlukla ayır
                name_parts = full_name.split(maxsplit=1)
                adi = name_parts[0] if len(name_parts) > 0 else ""
                soyadi = name_parts[1] if len(name_parts) > 1 else ""
            else:
                adi = row[column_mapping['adi']] if column_mapping['adi'] < len(row) else ""
                soyadi = row[column_mapping['soyadi']] if column_mapping['soyadi'] < len(row) else ""
            
            # Kolonları eşleştir
            row_dict = {
                id_column_name: id_no,
                "Adı": adi,
                "Soyadı": soyadi,
                "TC Kimlik No": tc_value
            }
            
            # Tutar (varsa)
            if column_mapping['tutar'] >= 0 and column_mapping['tutar'] < len(row):
                raw_tutar = row[column_mapping['tutar']]
                raw_tutar = str(raw_tutar).replace('"', '').replace("'", "").replace(',', '.')
                row_dict["Aidat Tutarı"] = raw_tutar
            else:
                row_dict["Aidat Tutarı"] = "0"
            
            cleaned_rows.append(row_dict)
            
        except Exception:
            continue
    
    df = pd.DataFrame(cleaned_rows)
    
    # Tutarı sayıya çevir
    try:
        df["Aidat Tutarı"] = pd.to_numeric(df["Aidat Tutarı"], errors='coerce').fillna(0)
    except:
        pass
    
    return df

# -----------------------------------------------------------------------------
# 4. ARAYÜZ VE DOSYA YÜKLEME
# -----------------------------------------------------------------------------

# ID Kolon Adı Seçimi
st.subheader("⚙️ Ayarlar")
id_column_choice = st.radio(
    "ID Kolonu Adı:",
    options=["Üye No", "Personel No"],
    horizontal=True
)

st.markdown("---")

uploaded_file = st.file_uploader("📤 Dosyayı Yükle", type=["csv", "xlsx", "txt", "xls"])

if uploaded_file is not None:
    st.info("📊 Dosya okunuyor...")
    
    string_data = ""
    
    try:
        # Excel Okuma
        if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            try:
                df_temp = pd.read_excel(uploaded_file, header=None, dtype=str)
                string_data = df_temp.to_csv(index=False, header=False, sep=';')
            except Exception as excel_error:
                st.error(f"Excel hatası: {excel_error}")
        
        # Metin Okuma
        else:
            raw_bytes = uploaded_file.getvalue()
            for encoding in ["cp1254", "utf-8", "iso-8859-9", "latin-1"]:
                try:
                    string_data = raw_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
        
        # Ham veriyi parse et
        if string_data:
            raw_data = parse_raw_data(string_data)
            
            if not raw_data:
                st.error("❌ TC Kimlik No içeren satır bulunamadı.")
            else:
                st.success(f"✅ {len(raw_data)} satır bulundu!")
                
                # Kolon sayısını bul (en fazla kolona sahip satır)
                max_cols = max(len(row) for row in raw_data)
                
                # Örnek veri göster - tüm kolonları göstermek için en uzun satırları seç
                st.subheader("🔍 Ham Veri Önizlemesi (İlk 5 Satır)")
                
                # İlk 5 satırı normalize et (eksik kolonları boş string ile doldur)
                preview_data = []
                for row in raw_data[:5]:
                    normalized_row = list(row) + [''] * (max_cols - len(row))
                    preview_data.append(normalized_row)
                
                preview_df = pd.DataFrame(preview_data)
                preview_df.columns = [f"Kolon {i}" for i in range(max_cols)]
                st.dataframe(preview_df, use_container_width=True)
                
                st.info(f"📊 Toplam {max_cols} kolon tespit edildi.")
                
                st.markdown("---")
                st.subheader("🗂️ Kolon Eşleştirme")
                st.info("👉 Aşağıda her bilginin hangi kolonda olduğunu seçin (Kolon 0'dan başlar)")
                
                # Ad-Soyad aynı kolonda mı?
                same_column = st.checkbox(
                    "✅ Ad ve Soyad aynı kolonda (örn: 'Ahmet Yılmaz')",
                    value=False,
                    help="İşaretlerseniz, tek bir kolon seçip otomatik olarak ad-soyad ayırması yapılır"
                )
                
                st.markdown("##### Kolonları Seçin:")
                
                if same_column:
                    # Ad-Soyad birlikte
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        id_col = st.number_input(
                            f"📌 {id_column_choice}",
                            min_value=0,
                            max_value=max_cols-1,
                            value=0,
                            help="Üye veya Personel No'nun bulunduğu kolon"
                        )
                    
                    with col2:
                        name_col = st.number_input(
                            "👤 Ad Soyad (Birlikte)",
                            min_value=0,
                            max_value=max_cols-1,
                            value=min(1, max_cols-1),
                            help="Ad ve soyadın birlikte bulunduğu kolon"
                        )
                        surname_col = name_col  # Aynı kolon
                    
                    with col3:
                        amount_col = st.number_input(
                            "💰 Aidat Tutarı",
                            min_value=0,
                            max_value=max_cols-1,
                            value=min(2, max_cols-1),
                            help="Tutar bilgisinin bulunduğu kolon"
                        )
                
                else:
                    # Ad-Soyad ayrı
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        id_col = st.number_input(
                            f"📌 {id_column_choice}",
                            min_value=0,
                            max_value=max_cols-1,
                            value=0,
                            help="Üye veya Personel No'nun bulunduğu kolon"
                        )
                    
                    with col2:
                        name_col = st.number_input(
                            "👤 Adı",
                            min_value=0,
                            max_value=max_cols-1,
                            value=min(1, max_cols-1),
                            help="İsmin bulunduğu kolon"
                        )
                    
                    with col3:
                        surname_col = st.number_input(
                            "👥 Soyadı",
                            min_value=0,
                            max_value=max_cols-1,
                            value=min(2, max_cols-1),
                            help="Soyadının bulunduğu kolon"
                        )
                    
                    with col4:
                        amount_col = st.number_input(
                            "💰 Aidat Tutarı",
                            min_value=0,
                            max_value=max_cols-1,
                            value=min(4, max_cols-1),
                            help="Tutar bilgisinin bulunduğu kolon"
                        )
                
                # Temizleme butonu
                if st.button("🚀 Veriyi Temizle ve Düzenle", type="primary", use_container_width=True):
                    
                    column_mapping = {
                        'id_no': id_col,
                        'adi': name_col,
                        'soyadi': surname_col,
                        'tutar': amount_col
                    }
                    
                    df_clean = clean_data_with_mapping(raw_data, column_mapping, id_column_choice, same_column=same_column)
                    
                    if not df_clean.empty:
                        st.success(f"✨ Başarılı! Toplam {len(df_clean)} kişi düzenlendi.")
                        st.dataframe(df_clean, use_container_width=True)
                        
                        # Excel İndir
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_clean.to_excel(writer, index=False, sheet_name='Temiz Liste')
                            workbook = writer.book
                            worksheet = writer.sheets['Temiz Liste']
                            
                            # Başlık Formatı
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
                        
                        file_prefix = "Uye" if id_column_choice == "Üye No" else "Personel"
                        
                        st.download_button(
                            label="📥 Temiz Excel İndir",
                            data=buffer,
                            file_name=f"BMS_Sendika_{file_prefix}_Temiz.xlsx",
                            mime="application/vnd.ms-excel",
                            use_container_width=True
                        )
                    else:
                        st.error("❌ Veri temizlenemedi. Kolon eşleştirmelerini kontrol edin.")
                
    except Exception as e:
        st.error(f"❌ Hata: {e}")
        st.exception(e)
