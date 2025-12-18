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
    st.info("👇 Dosyanızdaki sütunları uygun alanlara eşleştirin")
    
    # Ham verinin önizlemesi
    with st.expander("📋 Ham Veri Önizleme (İlk 5 Satır)", expanded=True):
        st.dataframe(df_sample.head(), use_container_width=True)
    
    # Mevcut sütun listesi
    available_columns = ["-- Seçilmedi --"] + list(df_sample.columns)
    
    # Eşleştirme formu
    st.markdown("#### Sütunları Eşleştir")
    
    col_left, col_right = st.columns(2)
    
    mapping = {}
    
    # İki sütuna bölerek selectbox'ları yerleştir
    items = list(required_columns.items())
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
                mapping[internal_key] = selected
    
    # Otomatik algılama önerisi göster
    with st.expander("💡 Akıllı Öneri", expanded=False):
        suggestions = auto_suggest_columns(df_sample, required_columns)
        if suggestions:
            st.markdown("**Önerilen Eşleşmeler:**")
            for key, col in suggestions.items():
                st.markdown(f"- `{[k for k, v in required_columns.items() if v == key][0]}` → **{col}**")
            
            if st.button("🎯 Önerileri Uygula", use_container_width=True):
                for key, col in suggestions.items():
                    st.session_state[f"map_{key}"] = col
                st.rerun()
    
    return mapping


def auto_suggest_columns(df, required_columns):
    """
    Sütun isimlerine göre otomatik eşleştirme önerisi yapar.
    
    Args:
        df (pd.DataFrame): Ham veri
        required_columns (dict): Gerekli sütunlar
    
    Returns:
        dict: Önerilen eşleşmeler
    """
    suggestions = {}
    
    # Arama anahtar kelimeleri
    keywords = {
        'member_no': ['üye', 'no', 'uye', 'member', 'id', 'sicil'],
        'first_name': ['ad', 'adi', 'name', 'first', 'isim'],
        'last_name': ['soyad', 'soyadi', 'surname', 'last'],
        'tc_no': ['tc', 'kimlik', 'tckimlik', 'identity', 'tcno'],
        'amount': ['tutar', 'aidat', 'miktar', 'amount', 'price', 'fiyat', 'ücret']
    }
    
    for col in df.columns:
        col_lower = str(col).lower()
        
        for internal_key in required_columns.values():
            if internal_key in keywords:
                for keyword in keywords[internal_key]:
                    if keyword in col_lower:
                        suggestions[internal_key] = col
                        break
    
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

