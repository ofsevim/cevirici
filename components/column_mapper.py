"""
Kolon eşleştirme UI componenti
"""
import streamlit as st


def render_column_mapper(column_info, target_columns):
    """
    Kolon eşleştirme arayüzünü render eder
    
    Args:
        column_info: Kaynak kolonlar hakkında bilgi (detect_columns'dan)
        target_columns: Hedef kolon isimleri listesi
        
    Returns:
        dict: {hedef_kolon: kaynak_kolon_index} formatında mapping
    """
    st.markdown("### 🎯 Kolon Eşleştirme")
    st.markdown("Her hedef kolonu dosyanızdaki bir kolonla eşleştirin:")
    
    # Modern stil için CSS
    st.markdown("""
    <style>
        .column-mapper {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .mapper-title {
            color: white;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .stSelectbox {
            background-color: white !important;
        }
        .column-preview {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            border-left: 4px solid #667eea;
        }
        .sample-data {
            font-size: 12px;
            color: #6c757d;
            margin-top: 5px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    column_mapping = {}
    
    # Her hedef kolon için seçim kutusu
    cols = st.columns([1, 2])
    
    with cols[0]:
        st.markdown("**Hedef Kolon**")
    with cols[1]:
        st.markdown("**Kaynak Kolon**")
    
    st.divider()
    
    for target_col in target_columns:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Hedef kolon ismi
            icon = get_column_icon(target_col)
            st.markdown(f"### {icon} {target_col}")
        
        with col2:
            # Kaynak kolon seçimi
            options = ["Seçilmedi"] + [
                f"Kolon {info['index'] + 1} ({info['type']})" 
                for info in column_info
            ]
            
            # Otomatik eşleştirme önerisi
            suggested_idx = suggest_column_match(target_col, column_info)
            default_index = suggested_idx + 1 if suggested_idx is not None else 0
            
            selected = st.selectbox(
                f"{target_col} için kaynak kolon",
                options=options,
                index=default_index,
                key=f"map_{target_col}",
                label_visibility="collapsed"
            )
            
            # Seçilen kolonun örnek verileri
            if selected != "Seçilmedi":
                col_idx = int(selected.split()[1]) - 1
                col_data = next((c for c in column_info if c['index'] == col_idx), None)
                
                if col_data:
                    column_mapping[target_col] = col_idx
                    
                    # Örnek verileri göster
                    with st.expander("📋 Önizleme", expanded=False):
                        st.markdown("**Örnek Veriler:**")
                        for sample in col_data['samples'][:3]:
                            st.code(sample, language=None)
            else:
                column_mapping[target_col] = None
    
    return column_mapping


def suggest_column_match(target_col, column_info):
    """
    Hedef kolon için en uygun kaynak kolonu önerir
    
    Args:
        target_col: Hedef kolon ismi
        column_info: Kaynak kolon bilgileri
        
    Returns:
        int: Önerilen kolon index'i veya None
    """
    # TC Kimlik için 11 haneli sayı ara
    if target_col == "TC Kimlik No":
        for col in column_info:
            if col['type'] == 'tc_kimlik':
                return col['index']
    
    # Tutar için numeric veya currency ara
    elif target_col == "Aidat Tutarı":
        for col in column_info:
            if col['type'] in ['currency', 'numeric']:
                return col['index']
    
    # Üye No için numeric ara (TC'den önce gelen)
    elif target_col == "Üye No":
        numeric_cols = [c for c in column_info if c['type'] == 'numeric']
        if numeric_cols:
            return numeric_cols[0]['index']
    
    return None


def get_column_icon(column_name):
    """
    Kolon ismine göre emoji icon döndürür
    
    Args:
        column_name: Kolon ismi
        
    Returns:
        str: Emoji
    """
    icons = {
        "Üye No": "🔢",
        "Adı": "👤",
        "Soyadı": "👨‍💼",
        "TC Kimlik No": "🆔",
        "Aidat Tutarı": "💰"
    }
    return icons.get(column_name, "📋")


def render_preview_table(df, max_rows=10):
    """
    DataFrame önizlemesi gösterir (modern stil)
    
    Args:
        df: Gösterilecek DataFrame
        max_rows: Maksimum satır sayısı
    """
    st.markdown("### 📊 Veri Önizleme")
    
    # Özet bilgiler
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam Satır", len(df))
    with col2:
        st.metric("Toplam Kolon", len(df.columns))
    with col3:
        # Dolu hücre oranı
        filled_ratio = (df.notna().sum().sum() / (len(df) * len(df.columns))) * 100
        st.metric("Dolu Hücre", f"{filled_ratio:.1f}%")
    
    st.divider()
    
    # Tablo önizleme
    st.dataframe(
        df.head(max_rows),
        use_container_width=True,
        hide_index=True
    )
    
    if len(df) > max_rows:
        st.info(f"İlk {max_rows} satır gösteriliyor. Toplam {len(df)} satır var.")

