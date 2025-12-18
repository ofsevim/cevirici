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
# 2. VERİ TEMİZLEME FONKSİYONU
# -----------------------------------------------------------------------------
def clean_and_parse_data_v3(file_content):
    data_rows = []
    
    lines = file_content.splitlines()
    
    for line in lines:
        # TC Kimlik bul (11 hane)
        tc_match = re.search(r'(?<!\d)\d{11}(?!\d)', line)
        
        if tc_match:
            try:
                tc_value = tc_match.group(0)
                
                # Ayırıcıyı belirle (Noktalı virgül öncelikli)
                if ";" in line:
                    parts = line.split(';')
                else:
                    parts = line.split(',')
                
                # Temizle
                clean_parts = [p.strip() for p in parts if p.strip()]
                
                # TC index bul
                try:
                    tc_index = clean_parts.index(tc_value)
                except ValueError:
                    continue 

                # --- VERİ ATAMA ---
                
                # Tutar (Temizlenmiş)
                tutar = "0"
                if len(clean_parts) > tc_index + 1:
                    raw_tutar = clean_parts[tc_index + 1]
                    raw_tutar = raw_tutar.replace('"', '').replace("'", "") # Tırnak sil
                    tutar = raw_tutar.replace(',', '.') # Virgülü nokta yap
                
                # Soyadı
                soyadi = ""
                if tc_index > 0:
                    soyadi = clean_parts[tc_index - 1]
                    soyadi = fix_turkish_chars(soyadi) # Türkçe karakter düzelt
                
                # Adı
                adi = ""
                if tc_index > 1:
                    adi = clean_parts[tc_index - 2]
                    adi = fix_turkish_chars(adi) # Türkçe karakter düzelt
                
                # Üye No
                uye_no = ""
                if tc_index > 2:
                    uye_no = clean_parts[tc_index - 3]
                else:
                    uye_no = clean_parts[0] if tc_index > 0 else ""

                row_dict = {
                    "Üye No": uye_no,
                    "Adı": adi,
                    "Soyadı": soyadi,
                    "TC Kimlik No": tc_value,
                    "Aidat Tutarı": tutar
                }
                data_rows.append(row_dict)
                
            except Exception as e:
                continue

    # DataFrame oluştur
    df = pd.read_json(io.StringIO(pd.DataFrame(data_rows).to_json(orient='records')))
    
    # Tutarı sayıya çevir
    try:
        df["Aidat Tutarı"] = pd.to_numeric(df["Aidat Tutarı"])
    except:
        pass

    return df

# -----------------------------------------------------------------------------
# 3. ARAYÜZ VE DOSYA YÜKLEME
# -----------------------------------------------------------------------------
uploaded_file = st.file_uploader("Dosyayı Yükle", type=["csv", "xlsx", "txt", "xls"])

if uploaded_file is not None:
    st.info("Dosya analiz ediliyor...")
    
    string_data = ""
    
    try:
        # Excel Okuma
        if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            try:
                # Excel'i oku
                df_temp = pd.read_excel(uploaded_file, header=None, dtype=str)
                # CSV stringe çevir (noktalı virgül ile)
                string_data = df_temp.to_csv(index=False, header=False, sep=';')
            except Exception as excel_error:
                st.error(f"Excel hatası: {excel_error}")
        
        # Metin Okuma (Encoding Denemeleri)
        else:
            raw_bytes = uploaded_file.getvalue()
            # 1. Öncelik: Türkçe Windows (Excel CSV'leri genelde budur)
            try:
                string_data = raw_bytes.decode("cp1254")
            except UnicodeDecodeError:
                # 2. Öncelik: UTF-8
                try:
                    string_data = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    # 3. Öncelik: ISO-8859-9 (Alternatif Türkçe)
                    try:
                        string_data = raw_bytes.decode("iso-8859-9")
                    except UnicodeDecodeError:
                         string_data = raw_bytes.decode("latin-1")
        
        # Temizle ve Göster
        if string_data:
            df_clean = clean_and_parse_data_v3(string_data)
            
            if not df_clean.empty:
                st.success(f"Başarılı! Toplam {len(df_clean)} kişi listelendi.")
                st.dataframe(df_clean)
                
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
                    data=buffer,
                    file_name="BMS_Sendika_Temiz.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.error("TC Kimlik No bulunamadı.")
                
    except Exception as e:
        st.error(f"Beklenmeyen hata: {e}")