"""
Sendika Kesinti Listesi Düzenleyici - Ana Uygulama
Modern kolon eşleştirme özelliği ile
"""
import streamlit as st
import pandas as pd

# Local modüller
from utils.file_handler import read_uploaded_file, detect_columns
from utils.data_processor import map_columns_to_target
from components.column_mapper import render_column_mapper, render_preview_table
from components.export_handler import render_export_section

# -----------------------------------------------------------------------------
# SAYFA YAPISI
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sendika Kesinti Listesi Düzenleyici",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS stilleri
st.markdown("""
<style>
    /* Ana tema renkleri */
    :root {
        --primary-color: #667eea;
        --secondary-color: #764ba2;
    }
    
    /* Başlık stilleri */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-size: 2.5rem;
    }
    
    .main-header p {
        color: #f0f0f0;
        margin: 10px 0 0 0;
    }
    
    /* Adım göstergeleri */
    .step-indicator {
        background: white;
        border-left: 4px solid #667eea;
        padding: 15px;
        margin: 20px 0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Upload alanı */
    .uploadedFile {
        border: 2px dashed #667eea !important;
        border-radius: 10px !important;
    }
    
    /* Butonlar */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
    }
    
    /* Metrikler */
    .stMetric {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* DataFrames */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# BAŞLIK VE AÇIKLAMA
# -----------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>📊 Sendika Kesinti Listesi Düzenleyici</h1>
    <p>Kolon eşleştirme ile her formattaki dosyayı düzenleyin</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - Bilgilendirme
with st.sidebar:
    st.markdown("### 📖 Nasıl Kullanılır?")
    st.markdown("""
    1. **Dosya Yükle**: CSV veya Excel dosyanızı yükleyin
    2. **Önizleme**: Verilerinizi kontrol edin
    3. **Kolon Eşleştir**: Her kolonu hedef alan ile eşleştirin
    4. **İndir**: Temizlenmiş dosyayı indirin
    """)
    
    st.divider()
    
    st.markdown("### ⚙️ Desteklenen Formatlar")
    st.markdown("""
    - Excel (.xlsx, .xls)
    - CSV (virgül, noktalı virgül, tab)
    - Text (.txt)
    """)
    
    st.divider()
    
    st.markdown("### 🎯 Hedef Kolonlar")
    st.markdown("""
    - Üye No
    - Adı
    - Soyadı
    - TC Kimlik No
    - Aidat Tutarı
    """)

# -----------------------------------------------------------------------------
# SESSION STATE YÖNETİMİ
# -----------------------------------------------------------------------------
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'df_raw' not in st.session_state:
    st.session_state.df_raw = None
if 'column_info' not in st.session_state:
    st.session_state.column_info = None
if 'df_processed' not in st.session_state:
    st.session_state.df_processed = None

# Hedef kolonlar
TARGET_COLUMNS = ["Üye No", "Adı", "Soyadı", "TC Kimlik No", "Aidat Tutarı"]

# -----------------------------------------------------------------------------
# ADIM 1: DOSYA YÜKLEME
# -----------------------------------------------------------------------------
st.markdown("""
<div class="step-indicator">
    <h3>🗂️ Adım 1: Dosya Yükleme</h3>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Dosyanızı buraya sürükleyin veya seçin",
    type=["csv", "xlsx", "txt", "xls"],
    help="CSV, Excel veya Text formatında dosya yükleyebilirsiniz"
)

if uploaded_file is not None:
    # Dosyayı oku
    if st.session_state.df_raw is None:
        with st.spinner("Dosya okunuyor..."):
            df, error = read_uploaded_file(uploaded_file)
            
            if error:
                st.error(f"❌ {error}")
            else:
                st.session_state.df_raw = df
                st.session_state.column_info = detect_columns(df)
                st.session_state.step = 2
                st.success(f"✅ Dosya başarıyla yüklendi! ({len(df)} satır, {len(df.columns)} kolon)")
    
    # -----------------------------------------------------------------------------
    # ADIM 2: VERİ ÖNİZLEME VE KOLON ALGILAMA
    # -----------------------------------------------------------------------------
    if st.session_state.step >= 2 and st.session_state.df_raw is not None:
        st.markdown("""
        <div class="step-indicator">
            <h3>👁️ Adım 2: Veri Önizleme</h3>
        </div>
        """, unsafe_allow_html=True)
        
        render_preview_table(st.session_state.df_raw, max_rows=15)
        
        st.divider()
        
        # -----------------------------------------------------------------------------
        # ADIM 3: KOLON EŞLEŞTİRME
        # -----------------------------------------------------------------------------
        st.markdown("""
        <div class="step-indicator">
            <h3>🔗 Adım 3: Kolon Eşleştirme</h3>
        </div>
        """, unsafe_allow_html=True)
        
        column_mapping = render_column_mapper(
            st.session_state.column_info,
            TARGET_COLUMNS
        )
        
        # İşleme butonu
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("✨ Verileri İşle", use_container_width=True, type="primary"):
                # En az bir kolon eşleşmeli
                if all(v is None for v in column_mapping.values()):
                    st.error("❌ Lütfen en az bir kolon eşleştirmesi yapın!")
                else:
                    with st.spinner("Veriler işleniyor..."):
                        try:
                            df_processed = map_columns_to_target(
                                st.session_state.df_raw,
                                column_mapping
                            )
                            st.session_state.df_processed = df_processed
                            st.session_state.step = 4
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ İşlem sırasında hata oluştu: {str(e)}")
        
        # -----------------------------------------------------------------------------
        # ADIM 4: SONUÇ VE EXPORT
        # -----------------------------------------------------------------------------
        if st.session_state.step >= 4 and st.session_state.df_processed is not None:
            st.divider()
            
            st.markdown("""
            <div class="step-indicator">
                <h3>🎉 Adım 4: İşlenmiş Veriler</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # İşlenmiş verileri göster
            st.markdown("### ✅ Temizlenmiş Veriler")
            st.dataframe(
                st.session_state.df_processed,
                use_container_width=True,
                hide_index=True
            )
            
            st.divider()
            
            # Export seçenekleri
            render_export_section(st.session_state.df_processed)
            
            # Yeni işlem butonu
            st.divider()
            if st.button("🔄 Yeni Dosya Yükle", use_container_width=True):
                # Session state'i temizle
                st.session_state.step = 1
                st.session_state.df_raw = None
                st.session_state.column_info = None
                st.session_state.df_processed = None
                st.rerun()

# -----------------------------------------------------------------------------
# ALT BİLGİ
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>💡 <strong>İpucu:</strong> Dosyanızın ilk satırı başlık içermiyorsa da sorun yok, 
    sistem otomatik olalgılar.</p>
    <p style="margin-top: 10px;">Made with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)
