"""
Veri İşleme Yardımcı Fonksiyonlar
Bu modül, dosya okuma, karakter düzeltme ve veri temizleme işlemlerini içerir.
"""

import pandas as pd
import re


def fix_turkish_chars(text):
    """
    Bozuk encoding'den kaynaklı Türkçe karakter hatalarını düzeltir.
    
    Args:
        text (str): Düzeltilecek metin
    
    Returns:
        str: Düzeltilmiş metin
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


def read_file_with_encoding(uploaded_file, skip_rows=0):
    """
    Yüklenen dosyayı uygun encoding ile okur.
    Excel ve metin dosyalarını destekler.
    
    Args:
        uploaded_file: Streamlit file uploader objesi
        skip_rows (int): Atlanacak başlangıç satır sayısı
    
    Returns:
        pd.DataFrame: Ham veri DataFrame'i
    """
    
    # Excel dosyası kontrolü
    if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
        try:
            df = pd.read_excel(uploaded_file, header=None, dtype=str, skiprows=skip_rows)
            # Tamamen boş satırları temizle
            df = df.dropna(how='all').reset_index(drop=True)
            # Tamamen boş sütunları temizle
            df = df.dropna(axis=1, how='all')
            # Sütun numaralarını yeniden düzenle
            df.columns = range(len(df.columns))
            return df
        except Exception as e:
            raise ValueError(f"Excel okuma hatası: {e}")
    
    # Metin dosyası (CSV/TXT) için encoding denemeleri
    raw_bytes = uploaded_file.getvalue()
    
    encodings = ['cp1254', 'utf-8', 'iso-8859-9', 'latin-1']
    
    for enc in encodings:
        try:
            string_data = raw_bytes.decode(enc)
            
            # Atlanacak satırları çıkar
            if skip_rows > 0:
                lines = string_data.split('\n')
                string_data = '\n'.join(lines[skip_rows:])
            
            # Ayırıcıyı tespit et
            if ';' in string_data.split('\n')[0]:
                separator = ';'
            elif ',' in string_data.split('\n')[0]:
                separator = ','
            elif '\t' in string_data.split('\n')[0]:
                separator = '\t'
            else:
                separator = ','
            
            # DataFrame'e dönüştür
            from io import StringIO
            df = pd.read_csv(StringIO(string_data), sep=separator, header=None, dtype=str, engine='python')
            
            # Tamamen boş satırları temizle
            df = df.dropna(how='all').reset_index(drop=True)
            # Tamamen boş sütunları temizle
            df = df.dropna(axis=1, how='all')
            # Sütun numaralarını yeniden düzenle
            df.columns = range(len(df.columns))
            
            return df
            
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    
    raise ValueError("Dosya okunamadı. Desteklenen formatlar: CSV, TXT, XLSX, XLS")


def clean_amount_value(value):
    """
    Tutar değerini temizler ve sayıya çevirir.
    
    Args:
        value (str): Ham tutar değeri
    
    Returns:
        float: Temizlenmiş tutar
    """
    if pd.isna(value) or value == "":
        return 0.0
    
    value_str = str(value)
    
    # Tırnak işaretlerini temizle
    value_str = value_str.replace('"', '').replace("'", "").strip()
    
    # Virgülü noktaya çevir
    value_str = value_str.replace(',', '.')
    
    # Sadece sayı ve nokta bırak
    value_str = re.sub(r'[^\d.]', '', value_str)
    
    try:
        return float(value_str)
    except ValueError:
        return 0.0


def clean_tc_number(value):
    """
    TC Kimlik numarasını temizler ve doğrular.
    
    Args:
        value (str): Ham TC değeri
    
    Returns:
        str: Temizlenmiş 11 haneli TC (geçerli değilse boş string)
    """
    if pd.isna(value):
        return ""
    
    value_str = str(value).strip()
    
    # Sadece rakamları al
    digits = re.sub(r'\D', '', value_str)
    
    # 11 hane kontrolü
    if len(digits) == 11:
        return digits
    
    return ""


def apply_column_mapping(df_raw, column_mapping):
    """
    Kullanıcının yaptığı sütun eşleştirmesine göre veriyi işler.
    
    Args:
        df_raw (pd.DataFrame): Ham veri
        column_mapping (dict): Sütun eşleştirme haritası
    
    Returns:
        pd.DataFrame: Temizlenmiş ve yapılandırılmış veri
    """
    
    processed_data = []
    
    for idx, row in df_raw.iterrows():
        try:
            # Her alan için mapping'e göre veriyi al
            member_no = str(row[column_mapping.get('member_no', 0)]).strip() if 'member_no' in column_mapping else ""
            first_name = str(row[column_mapping.get('first_name', 0)]).strip() if 'first_name' in column_mapping else ""
            last_name = str(row[column_mapping.get('last_name', 0)]).strip() if 'last_name' in column_mapping else ""
            tc_no = str(row[column_mapping.get('tc_no', 0)]).strip() if 'tc_no' in column_mapping else ""
            amount = str(row[column_mapping.get('amount', 0)]).strip() if 'amount' in column_mapping else "0"
            
            # Türkçe karakter düzeltmeleri
            first_name = fix_turkish_chars(first_name)
            last_name = fix_turkish_chars(last_name)
            
            # TC temizle
            tc_no = clean_tc_number(tc_no)
            
            # Tutar temizle
            amount_clean = clean_amount_value(amount)
            
            # Geçerli TC varsa ekle
            if tc_no and len(tc_no) == 11:
                processed_data.append({
                    "Üye No": member_no,
                    "Adı": first_name,
                    "Soyadı": last_name,
                    "TC Kimlik No": tc_no,
                    "Aidat Tutarı": amount_clean
                })
        
        except Exception:
            # Hatalı satırları atla
            continue
    
    # DataFrame oluştur
    df_clean = pd.DataFrame(processed_data)
    
    return df_clean


def detect_file_structure(df_raw, sample_size=50):
    """
    Ham veriyi analiz eder ve sütun yapısı hakkında bilgi verir.
    
    Args:
        df_raw (pd.DataFrame): Ham veri
        sample_size (int): Analiz edilecek satır sayısı
    
    Returns:
        dict: Dosya yapısı bilgileri
    """
    
    info = {
        'total_rows': len(df_raw),
        'total_columns': len(df_raw.columns),
        'has_tc_column': False,
        'tc_column_index': None,
        'has_amount_column': False,
        'sample_data': df_raw.head(sample_size)
    }
    
    # TC Kimlik içeren sütun var mı?
    for col_idx, col in enumerate(df_raw.columns):
        sample_values = df_raw[col].astype(str).head(sample_size)
        
        # TC pattern (11 hane)
        tc_count = sample_values.str.match(r'^\d{11}$').sum()
        
        if tc_count > sample_size * 0.5:  # %50'den fazlası TC ise
            info['has_tc_column'] = True
            info['tc_column_index'] = col_idx
            break
    
    # Tutar içeren sütun var mı?
    for col in df_raw.columns:
        sample_values = df_raw[col].astype(str).head(sample_size)
        
        # Sayısal pattern
        numeric_count = sample_values.str.match(r'^[\d\.,]+$').sum()
        
        if numeric_count > sample_size * 0.5:
            info['has_amount_column'] = True
            break
    
    return info

