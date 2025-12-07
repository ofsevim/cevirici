import streamlit as st
import pandas as pd
import io
import re

# Sayfa Ayarları
st.set_page_config(page_title="Akıllı Sendika Listesi", page_icon="🧠")

st.title("🧠 Yapay Zeka Destekli Liste Düzenleyici")
st.write("Dosyanızı yükleyin. Sütunların yeri nerede olursa olsun otomatik bulur.")

uploaded_file = st.file_uploader("Dosyanızı buraya bırakın", type=["xls", "xlsx", "csv"])

# --- YARDIMCI FONKSİYONLAR ---
def is_tc(val):
    """Bir değerin TC Kimlik No olup olmadığını kontrol eder."""
    s = str(val).split('.')[0].strip()
    return s.isdigit() and len(s) == 11 and s[0] != '0'

def is_money(val):
    """Bir değerin para birimi olup olmadığını kontrol eder."""
    s = str(val).replace('TL', '').replace(' ', '').strip()
    # 123,45 veya 123.45 formatı
    if re.match(r'^\d+([.,]\d{1,2})?$', s):
        return True
    return False

def is_sira_no(val):
    """Sıra numarası gibi ardışık küçük sayı mı?"""
    try:
        n = int(float(str(val)))
        return 0 < n < 10000
    except:
        return False

def clean_money(x):
    if pd.isna(x): return 0.0
    x = str(x).replace('TL', '').replace(' ', '')
    if ',' in x and '.' in x: x = x.replace('.', '') 
    x = x.replace(',', '.')
    try: return float(x)
    except: return 0.0

def clean_text(x):
    return str(x).split('.')[0].strip() if pd.notna(x) else ""

def analyze_and_map_columns(df):
    """
    DataFrame içindeki sütunları analiz eder ve hangisinin ne olduğuna karar verir.
    Puanlama sistemi kullanır.
    """
    column_scores = {
        'Sira No': {},
        'TC Kimlik No': {},
        'Aidat Tutari': {},
        'Adi': {},
        'Soyadi': {},
        'Uye No': {}
    }
    
    # Sadece anlamlı (boş olmayan) satırlara bak
    # Rastgele 20 satırı örnekle (Hız için)
    sample_df = df.dropna(thresh=2).sample(n=min(30, len(df)), random_state=42)
    
    for col in df.columns:
        # Sütundaki verileri analiz et
        tc_score = 0
        money_score = 0
        sira_score = 0
        text_score = 0
        
        valid_count = 0
        for val in sample_df[col]:
            if pd.isna(val): continue
            valid_count += 1
            
            if is_tc(val): tc_score += 1
            if is_money(val) and not is_tc(val) and not is_sira_no(val): money_score += 1
            if is_sira_no(val): sira_score += 1
            if isinstance(val, str) and not any(c.isdigit() for c in val): text_score += 1
        
        if valid_count == 0: continue
        
        # Puanları oranla
        column_scores['TC Kimlik No'][col] = tc_score / valid_count
        column_scores['Aidat Tutari'][col] = money_score / valid_count
        column_scores['Sira No'][col] = sira_score / valid_count
        # İsim ve Soyad için metin yoğunluğuna bakacağız ama TC olmayan metinler
        column_scores['Adi'][col] = text_score / valid_count
        
    # --- EŞLEŞTİRME (EN YÜKSEK PUANLARI AL) ---
    mapping = {}
    used_cols = set()

    # 1. Önce en belirgin olanları bul: TC ve Aidat
    for field in ['TC Kimlik No', 'Aidat Tutari', 'Sira No']:
        best_col = max(column_scores[field], key=column_scores[field].get, default=None)
        if best_col is not None and column_scores[field][best_col] > 0.4: # %40 eşleşme eşiği
            mapping[field] = best_col
            used_cols.add(best_col)

    # 2. İsim ve Soyadı Bulma (Biraz daha karmaşık)
    # Genellikle İsim sütunu Soyad'dan önce gelir veya yan yanadır.
    # Metin puanı yüksek olan ve henüz kullanılmamış sütunları al.
    potential_text_cols = sorted(
        [c for c in column_scores['Adi'] if c not in used_cols and column_scores['Adi'][c] > 0.5],
        key=lambda x: x # İndex sırasına göre kalsın
    )
    
    if len(potential_text_cols) >= 2:
        mapping['Adi'] = potential_text_cols[0]
        mapping['Soyadi'] = potential_text_cols[1]
        used_cols.add(potential_text_cols[0])
        used_cols.add(potential_text_cols[1])
    elif len(potential_text_cols) == 1:
        mapping['Adi'] = potential_text_cols[0]
        # Soyadı bulunamadıysa Adı sütununu kopyala veya boş bırak
        mapping['Soyadi'] = None 

    # 3. Üye No (Genellikle Sıra No ile Adı arasında kalan sayıdır)
    # Bu zor bir alan, basitçe kalan sayısal sütunlardan birini seçelim
    # Veya spesifik bir mantık: 4-6 haneli sayılar
    uye_no_candidates = []
    for col in df.columns:
        if col in used_cols: continue
        score = 0
        count = 0
        for val in sample_df[col]:
            if pd.isna(val): continue
            s = str(val).split('.')[0]
            if s.isdigit() and 3 < len(s) < 8: # 4-7 haneli sayılar genelde üye nosudur
                score += 1
            count += 1
        if count > 0 and (score / count) > 0.5:
            uye_no_candidates.append(col)
            
    if uye_no_candidates:
        mapping['Uye No'] = uye_no_candidates[0]
    else:
        mapping['Uye No'] = None

    return mapping


def process_file(file):
    # --- OKUMA ---
    df = None
    file_name = file.name.lower()
    try:
        if file_name.endswith('.xlsx'):
            df = pd.read_excel(file, header=None, engine='openpyxl')
        elif file_name.endswith('.xls'):
            try:
                df = pd.read_excel(file, header=None, engine='xlrd')
            except:
                dfs = pd.read_html(file)
                if dfs: df = dfs[0]
        
        if df is None: # CSV veya Text dene
            file.seek(0)
            for enc in ['utf-8', 'cp1254', 'latin1']:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, header=None, encoding=enc, sep=None, engine='python')
                    break
                except: continue
                
        if df is None: return None, "Dosya okunamadı."
        
    except Exception as e: return None, str(e)

    # --- ANALİZ VE HARİTALAMA ---
    try:
        mapping = analyze_and_map_columns(df)
        
        # Eğer kritik alanlar (TC, Aidat) bulunamadıysa hata ver
        if 'TC Kimlik No' not in mapping or 'Aidat Tutari' not in mapping:
            return None, "Otomatik analiz başarısız oldu. Dosyada TC Kimlik veya Aidat sütunu tespit edilemedi."
            
        # Yeni DataFrame oluştur
        new_df = pd.DataFrame()
        
        if 'Sira No' in mapping:
            new_df['Sira No'] = df[mapping['Sira No']]
        else:
            new_df['Sira No'] = range(1, len(df) + 1) # Sıra no yoksa oluştur

        new_df['Uye No'] = df[mapping['Uye No']] if mapping.get('Uye No') is not None else ""
        new_df['Adi'] = df[mapping['Adi']] if mapping.get('Adi') is not None else ""
        new_df['Soyadi'] = df[mapping['Soyadi']] if mapping.get('Soyadi') is not None else ""
        new_df['TC Kimlik No'] = df[mapping['TC Kimlik No']]
        new_df['Aidat Tutari'] = df[mapping['Aidat Tutari']]

        # --- TEMİZLİK ---
        # 1. Başlık satırlarını ve boşlukları at (TC Kimlik No geçerli olanları tut)
        def is_valid_row(row):
            return is_tc(row['TC Kimlik No'])
            
        new_df = new_df[new_df.apply(is_valid_row, axis=1)].copy()
        
        # 2. Formatları düzelt
        new_df['Aidat Tutari'] = new_df['Aidat Tutari'].apply(clean_money)
        new_df['TC Kimlik No'] = new_df['TC Kimlik No'].apply(clean_text)
        new_df['Uye No'] = new_df['Uye No'].apply(clean_text)
        
        # Sıra No'yu yeniden ver (Temizlendikten sonra karışmasın)
        new_df['Sira No'] = range(1, len(new_df) + 1)

        return new_df, None

    except Exception as e:
        return None, f"İşleme hatası: {str(e)}"

# --- ARAYÜZ ---
if uploaded_file:
    with st.spinner('Yapay zeka sütunları analiz ediyor...'):
        df_result, error = process_file(uploaded_file)
        
        if error:
            st.error(f"Hata: {error}")
        else:
            st.success(f"Analiz Tamamlandı! {len(df_result)} kişi bulundu.")
            st.dataframe(df_result.head())
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_result.to_excel(writer, index=False)
                
            st.download_button("📥 Sonucu İndir", buffer.getvalue(), "Temiz_Liste.xlsx", "application/vnd.ms-excel")