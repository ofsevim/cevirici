"""
Dosya okuma ve encoding düzeltme fonksiyonları
"""
import pandas as pd
import io


def fix_turkish_chars(text):
    """
    Bozuk Türkçe karakterleri düzeltir (encoding sorunları için)
    
    Args:
        text: Düzeltilecek metin
        
    Returns:
        Düzeltilmiş metin
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


def read_uploaded_file(uploaded_file):
    """
    Yüklenen dosyayı okur ve DataFrame döndürür
    Çeşitli encoding ve format denemesi yapar
    
    Args:
        uploaded_file: Streamlit file uploader objesi
        
    Returns:
        tuple: (DataFrame, hata_mesajı)
    """
    try:
        # Excel dosyası
        if uploaded_file.name.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(uploaded_file, header=None, dtype=str)
                return df, None
            except Exception as e:
                return None, f"Excel okuma hatası: {str(e)}"
        
        # CSV/Text dosyası
        else:
            raw_bytes = uploaded_file.getvalue()
            encodings = ["cp1254", "utf-8", "iso-8859-9", "latin-1"]
            
            for encoding in encodings:
                try:
                    string_data = raw_bytes.decode(encoding)
                    
                    # Ayırıcıyı tespit et
                    if ";" in string_data[:1000]:
                        separator = ";"
                    elif "," in string_data[:1000]:
                        separator = ","
                    elif "\t" in string_data[:1000]:
                        separator = "\t"
                    else:
                        separator = ","
                    
                    df = pd.read_csv(io.StringIO(string_data), 
                                    sep=separator, 
                                    header=None,
                                    dtype=str,
                                    engine='python')
                    
                    return df, None
                    
                except Exception:
                    continue
            
            return None, "Dosya okunamadı. Desteklenen formatlardan biri değil."
                    
    except Exception as e:
        return None, f"Beklenmeyen hata: {str(e)}"


def detect_columns(df, max_rows=50):
    """
    DataFrame'deki kolonları analiz eder ve olası veri tiplerini tahmin eder
    
    Args:
        df: Pandas DataFrame
        max_rows: Analiz edilecek maksimum satır sayısı
        
    Returns:
        list: Her kolon için bilgi içeren dictionary listesi
    """
    column_info = []
    
    for col_idx in range(len(df.columns)):
        col_data = df.iloc[:max_rows, col_idx].dropna().astype(str)
        
        # Boş kolon kontrolü
        if len(col_data) == 0:
            continue
            
        # Örnek veriler
        sample_values = col_data.head(5).tolist()
        
        # Veri tipi tahmini
        data_type = "text"
        
        # TC Kimlik kontrolü (11 haneli sayı)
        if col_data.str.match(r'^\d{11}$').sum() > len(col_data) * 0.5:
            data_type = "tc_kimlik"
        
        # Sayı kontrolü
        elif col_data.str.replace('.', '').str.replace(',', '').str.match(r'^\d+$').sum() > len(col_data) * 0.7:
            data_type = "numeric"
        
        # Para birimi kontrolü
        elif col_data.str.contains(r'[\d,\.]+', regex=True).sum() > len(col_data) * 0.5:
            data_type = "currency"
        
        column_info.append({
            "index": col_idx,
            "label": f"Kolon {col_idx + 1}",
            "type": data_type,
            "samples": sample_values,
            "non_empty_count": len(col_data)
        })
    
    return column_info

