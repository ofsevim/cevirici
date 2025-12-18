"""
Veri işleme ve dönüştürme fonksiyonları
"""
import pandas as pd
import re
from .file_handler import fix_turkish_chars


def map_columns_to_target(df, column_mapping):
    """
    Kullanıcının seçtiği kolon eşleştirmesine göre DataFrame'i dönüştürür
    
    Args:
        df: Kaynak DataFrame
        column_mapping: {"hedef_kolon": kaynak_kolon_index} formatında dict
        
    Returns:
        DataFrame: Dönüştürülmüş DataFrame
    """
    result_data = []
    
    for idx, row in df.iterrows():
        row_dict = {}
        
        for target_col, source_idx in column_mapping.items():
            if source_idx is not None and source_idx != "":
                value = str(row.iloc[int(source_idx)]) if pd.notna(row.iloc[int(source_idx)]) else ""
                
                # Türkçe karakter düzeltmesi
                if target_col in ["Adı", "Soyadı"]:
                    value = fix_turkish_chars(value)
                
                # Tutar temizleme
                elif target_col == "Aidat Tutarı":
                    value = clean_amount(value)
                
                row_dict[target_col] = value
            else:
                row_dict[target_col] = ""
        
        result_data.append(row_dict)
    
    return pd.DataFrame(result_data)


def clean_amount(value):
    """
    Tutar değerini temizler ve sayıya çevrilmeye hazır hale getirir
    
    Args:
        value: Ham tutar değeri
        
    Returns:
        str: Temizlenmiş tutar
    """
    if not isinstance(value, str):
        return str(value)
    
    # Tırnak işaretlerini kaldır
    value = value.replace('"', '').replace("'", '').strip()
    
    # Virgülü noktaya çevir
    value = value.replace(',', '.')
    
    # Sadece sayı ve nokta bırak
    value = re.sub(r'[^\d.]', '', value)
    
    return value if value else "0"


def validate_tc_kimlik(tc_no):
    """
    TC Kimlik numarasının geçerliliğini kontrol eder
    
    Args:
        tc_no: TC Kimlik numarası (string)
        
    Returns:
        bool: Geçerli mi?
    """
    if not isinstance(tc_no, str):
        tc_no = str(tc_no)
    
    # 11 hane kontrolü
    if len(tc_no) != 11:
        return False
    
    # Sadece rakam kontrolü
    if not tc_no.isdigit():
        return False
    
    # İlk hane 0 olamaz
    if tc_no[0] == '0':
        return False
    
    return True


def process_legacy_format(file_content):
    """
    Eski format için regex tabanlı veri çıkarma (geriye dönük uyumluluk)
    
    Args:
        file_content: Ham dosya içeriği (string)
        
    Returns:
        DataFrame: İşlenmiş veri
    """
    data_rows = []
    lines = file_content.splitlines()
    
    for line in lines:
        # TC Kimlik bul (11 hane)
        tc_match = re.search(r'(?<!\d)\d{11}(?!\d)', line)
        
        if tc_match:
            try:
                tc_value = tc_match.group(0)
                
                # Ayırıcıyı belirle
                if ";" in line:
                    parts = line.split(';')
                else:
                    parts = line.split(',')
                
                clean_parts = [p.strip() for p in parts if p.strip()]
                
                try:
                    tc_index = clean_parts.index(tc_value)
                except ValueError:
                    continue
                
                # Tutar
                tutar = "0"
                if len(clean_parts) > tc_index + 1:
                    raw_tutar = clean_parts[tc_index + 1]
                    tutar = clean_amount(raw_tutar)
                
                # Soyadı
                soyadi = ""
                if tc_index > 0:
                    soyadi = fix_turkish_chars(clean_parts[tc_index - 1])
                
                # Adı
                adi = ""
                if tc_index > 1:
                    adi = fix_turkish_chars(clean_parts[tc_index - 2])
                
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
                
            except Exception:
                continue
    
    if data_rows:
        df = pd.DataFrame(data_rows)
        try:
            df["Aidat Tutarı"] = pd.to_numeric(df["Aidat Tutarı"])
        except:
            pass
        return df
    
    return pd.DataFrame()

