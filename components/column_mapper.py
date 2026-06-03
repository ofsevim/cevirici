"""
Sütun Eşleştirme Component
Bu modül, yüklenen dosyalardaki sütunların hedef alanlara eşleştirilmesi için UI sağlar.
"""

import streamlit as st
import pandas as pd


def render_column_mapper(df_sample, required_columns):
    """
    Sütun eşleştirme arayüzünü render eder.
    
    Args:
        df_sample (pd.DataFrame): Ham veri örneği (ilk birkaç satır)
        required_columns (dict): {'display_name': 'internal_key', ...} formatında gerekli sütunlar
    
    Returns:
        dict: Eşleştirilmiş sütun haritası {'internal_key': column_index/name, ...}
    """
    
    st.markdown("### 🔄 Sütun Eşleştirme")
    
    # Ad-Soyad birleşik mi kontrolü
    use_combined_name = st.checkbox(
        "📝 Ad ve Soyad tek sütunda (örn: 'Ahmet Yılmaz')",
        value=False,
        help="İsim ve soyisim aynı sütundaysa bu seçeneği işaretleyin"
    )
    
    st.info("👇 Dosyanızdaki sütunları uygun alanlara eşleştirin")
    
    # Ham verinin önizlemesi
    with st.expander("📋 Ham Veri Önizleme (İlk 10 Satır)", expanded=True):
        # Sütun numaralarını göster
        preview_df = df_sample.head(10).copy()
        
        # NaN/None değerlerini boş string ile değiştir (daha temiz görünüm)
        preview_df = preview_df.fillna("")
        
        preview_df.columns = [f"Sütun {i}" for i in range(len(preview_df.columns))]
        
        st.dataframe(
            preview_df,
            use_container_width=True,
            height=400
        )
        
        st.caption(f"📊 Toplam {len(df_sample)} satır, {len(df_sample.columns)} sütun")
        
        # Veri boşluk kontrolü
        non_empty_cells = df_sample.notna().sum().sum()
        total_cells = len(df_sample) * len(df_sample.columns)
        
        if non_empty_cells == 0:
            st.error("⚠️ Tüm hücreler boş! Lütfen 'Atlanan satır sayısı' değerini azaltın.")
        elif non_empty_cells < total_cells * 0.3:
            st.warning(f"⚠️ Verilerin çoğu boş ({non_empty_cells}/{total_cells} dolu). Satır atlama ayarını kontrol edin.")
    
    # Sütun seçeneklerini detaylı önizlemeyle oluştur
    def get_column_label(col_index, df):
        """Sütun için detaylı etiket oluştur (benzersiz örnek değerlerle)"""
        values = df[col_index].dropna().astype(str)
        # 'None', 'nan' gibi sahte değerleri filtrele
        values = values[~values.isin(['None', 'nan', 'NaN', ''])]
        unique_vals = values.unique()[:5]  # İlk 5 benzersiz değer
        
        if len(unique_vals) > 0:
            preview = ", ".join([str(v)[:20] for v in unique_vals])
            return f"Sütun {col_index}: {preview}"
        else:
            return f"Sütun {col_index}: (boş)"
    
    # Çoğunluğu boş olan sütunları filtrele (toplam satırın %10'undan az doluysa gizle)
    min_fill_count = max(1, len(df_sample) * 0.10)
    valid_col_indices = []
    for i in range(len(df_sample.columns)):
        non_null = df_sample[i].dropna()
        # 'None', 'nan' gibi sahte değerleri de say
        real_values = non_null[~non_null.astype(str).isin(['None', 'nan', 'NaN', ''])]
        if len(real_values) >= min_fill_count:
            valid_col_indices.append(i)
    
    # Mevcut sütun listesi (örnek değerlerle, boş sütunlar filtrelenmiş)
    available_columns = ["-- Seçilmedi --"] + [get_column_label(i, df_sample) for i in valid_col_indices]
    
    # Otomatik öneri hesapla
    suggestions = auto_suggest_columns(df_sample, required_columns, use_combined_name)
    
    # Eşleştirme formu
    st.markdown("#### Sütunları Eşleştir")
    
    col_left, col_right = st.columns(2)
    
    mapping = {}
    mapping['use_combined_name'] = use_combined_name
    
    # Eğer birleşik ad kullanılıyorsa, first_name ve last_name'i atlayıp full_name ekle
    if use_combined_name:
        items = [(k, v) for k, v in required_columns.items() if v not in ['first_name', 'last_name']]
        items.insert(1, ("Adı Soyadı (Birleşik)", "full_name"))
    else:
        items = list(required_columns.items())
    
    # Sütun index'ini label'dan çıkaran yardımcı fonksiyon
    def extract_col_index(label):
        """'Sütun X: ...' formatından X'i çıkar"""
        try:
            return int(label.split(":")[0].split(" ")[1])
        except:
            return None
    
    # Öneri sütun index'ini selectbox label'ına çeviren yardımcı
    def find_default_index(internal_key, available_cols, suggestions):
        """Otomatik öneri sonucuna göre selectbox'ın varsayılan index'ini bul"""
        if internal_key in suggestions:
            suggested_col = suggestions[internal_key]
            target_prefix = f"Sütun {suggested_col}:"
            for idx, label in enumerate(available_cols):
                if label.startswith(target_prefix):
                    return idx
        return 0  # "-- Seçilmedi --"
    
    # İki sütuna bölerek selectbox'ları yerleştir
    mid_point = (len(items) + 1) // 2
    
    with col_left:
        for display_name, internal_key in items[:mid_point]:
            default_idx = find_default_index(internal_key, available_columns, suggestions)
            selected = st.selectbox(
                f"**{display_name}** için sütun seç:",
                options=available_columns,
                index=default_idx,
                key=f"map_{internal_key}",
            )
            
            if selected != "-- Seçilmedi --":
                col_index = extract_col_index(selected)
                if col_index is not None:
                    mapping[internal_key] = col_index
    
    with col_right:
        for display_name, internal_key in items[mid_point:]:
            default_idx = find_default_index(internal_key, available_columns, suggestions)
            selected = st.selectbox(
                f"**{display_name}** için sütun seç:",
                options=available_columns,
                index=default_idx,
                key=f"map_{internal_key}",
            )
            
            if selected != "-- Seçilmedi --":
                col_index = extract_col_index(selected)
                if col_index is not None:
                    mapping[internal_key] = col_index
    
    return mapping


def auto_suggest_columns(df, required_columns, use_combined_name=False):
    """
    Sütun içeriğine göre otomatik eşleştirme önerisi yapar.
    
    Args:
        df (pd.DataFrame): Ham veri
        required_columns (dict): Gerekli sütunlar
        use_combined_name (bool): Ad-Soyad birleşik mi?
    
    Returns:
        dict: Önerilen eşleşmeler {internal_key: column_index}
    """
    suggestions = {}
    
    # Her sütunu analiz et
    for col_idx in range(len(df.columns)):
        # İlk 20 satırı sample olarak al
        sample_values = df[col_idx].astype(str).head(20)
        
        # TC Kimlik tespiti (11 haneli sayılar)
        if 'tc_no' not in suggestions:
            tc_pattern_count = sample_values.str.match(r'^\d{11}$').sum()
            if tc_pattern_count >= 5:  # En az 5 satır TC formatında
                suggestions['tc_no'] = col_idx
                continue
        
        # Tutar tespiti (sayısal değerler, virgül/nokta içeren)
        if 'amount' not in suggestions:
            amount_pattern_count = sample_values.str.match(r'^[\d\.,]+$').sum()
            if amount_pattern_count >= 5:
                suggestions['amount'] = col_idx
                continue
        
        # Üye No / Sıra No tespiti (1-6 haneli sayılar)
        if 'member_no' not in suggestions:
            member_pattern_count = sample_values.str.match(r'^\d{1,7}$').sum()
            if member_pattern_count >= 5:
                suggestions['member_no'] = col_idx
                continue
        
        # İsim tespiti (2 veya daha fazla kelime, boşluk içeren)
        if use_combined_name:
            if 'full_name' not in suggestions:
                # Birleşik isim tespiti (boşluk içeren isimler)
                combined_name_count = sample_values.str.match(r'^[A-Za-zÇçĞğİıÖöŞşÜü]+\s+[A-Za-zÇçĞğİıÖöŞşÜü]+').sum()
                if combined_name_count >= 5:
                    suggestions['full_name'] = col_idx
                    continue
        else:
            # Ayrı isim tespiti
            if 'first_name' not in suggestions or 'last_name' not in suggestions:
                name_pattern_count = sample_values.str.match(r'^[A-Za-zÇçĞğİıÖöŞşÜü\s]{2,30}$').sum()
                if name_pattern_count >= 5:
                    # Boşluk içermeyen veya tek kelime ise muhtemelen tek isim
                    single_word_count = sample_values.str.match(r'^[A-Za-zÇçĞğİıÖöŞşÜü]+$').sum()
                    if single_word_count >= 5:
                        if 'first_name' not in suggestions:
                            suggestions['first_name'] = col_idx
                        elif 'last_name' not in suggestions:
                            suggestions['last_name'] = col_idx
    
    return suggestions


def validate_mapping(mapping, required_columns):
    """
    Eşleştirmenin geçerli olup olmadığını kontrol eder.
    
    Args:
        mapping (dict): Kullanıcının yaptığı eşleştirme
        required_columns (dict): Gerekli sütunlar
    
    Returns:
        tuple: (is_valid: bool, missing_fields: list)
    """
    # Birleşik isim modu kontrolü
    use_combined_name = mapping.get('use_combined_name', False)
    
    if use_combined_name:
        # Birleşik isim modunda first_name ve last_name yerine full_name gerekli
        required_keys = set(required_columns.values()) - {'first_name', 'last_name'}
        required_keys.add('full_name')
    else:
        required_keys = set(required_columns.values())
    
    # use_combined_name'i mapped_keys'den çıkar (çünkü bu bir bool değer, sütun değil)
    mapped_keys = set(k for k in mapping.keys() if k != 'use_combined_name')
    
    missing = required_keys - mapped_keys
    
    return len(missing) == 0, list(missing)

