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
    
    # Mevcut sütun listesi (sütun numaraları ile)
    available_columns = ["-- Seçilmedi --"] + [f"Sütun {i}" for i in range(len(df_sample.columns))]
    
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
    
    # İki sütuna bölerek selectbox'ları yerleştir
    mid_point = (len(items) + 1) // 2
    
    with col_left:
        for display_name, internal_key in items[:mid_point]:
            selected = st.selectbox(
                f"**{display_name}** için sütun seç:",
                options=available_columns,
                key=f"map_{internal_key}",
                help=f"{display_name} bilgisinin bulunduğu sütunu seçin"
            )
            
            if selected != "-- Seçilmedi --":
                mapping[internal_key] = selected
    
    with col_right:
        for display_name, internal_key in items[mid_point:]:
            selected = st.selectbox(
                f"**{display_name}** için sütun seç:",
                options=available_columns,
                key=f"map_{internal_key}",
                help=f"{display_name} bilgisinin bulunduğu sütunu seçin"
            )
            
            if selected != "-- Seçilmedi --":
                # "Sütun 0" -> 0 dönüşümü
                col_index = int(selected.split(" ")[1])
                mapping[internal_key] = col_index
    
    # Otomatik algılama önerisi göster
    with st.expander("💡 Akıllı Öneri", expanded=False):
        suggestions = auto_suggest_columns(df_sample, required_columns, use_combined_name)
        if suggestions:
            st.markdown("**Önerilen Eşleşmeler:**")
            for key, col_idx in suggestions.items():
                if key == 'full_name':
                    display_name = "Adı Soyadı (Birleşik)"
                else:
                    matching_items = [k for k, v in required_columns.items() if v == key]
                    display_name = matching_items[0] if matching_items else key
                st.markdown(f"- `{display_name}` → **Sütun {col_idx}**")
            
            if st.button("🎯 Önerileri Uygula", use_container_width=True):
                for key, col_idx in suggestions.items():
                    st.session_state[f"map_{key}"] = f"Sütun {col_idx}"
                st.rerun()
    
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
    required_keys = set(required_columns.values())
    mapped_keys = set(mapping.keys())
    
    missing = required_keys - mapped_keys
    
    return len(missing) == 0, list(missing)

