"""
Sendika Kesinti Listesi Düzenleyici
Modern, modüler ve kullanıcı dostu veri temizleme uygulaması
"""

import streamlit as st
import pandas as pd
import io

# Component ve utility import
from components.column_mapper import render_column_mapper, validate_mapping
from utils.data_processor import (
    read_file_with_encoding,
    apply_column_mapping,
    detect_file_structure,
    find_data_start_row
)

# -----------------------------------------------------------------------------
# SAYFA AYARLARI VE STİL
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Veri Temizleyici Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #2563eb 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
        margin-top: 0;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .main-header img {
        width: 180px;
        height: 180px;
        object-fit: contain;
        -webkit-text-fill-color: initial;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 0.5rem;
    }
    .step-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        background: #3b82f6;
        color: white;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .block-container {
        padding-top: 1rem !important;
    }
    .element-container {
        margin-bottom: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# BAŞLIK VE AÇIKLAMA
# -----------------------------------------------------------------------------
st.markdown('<h1 class="main-header"><img src="https://buromemursen.org.tr/uploads/logo.gif" alt="Büro Memur-Sen"> Sendika Kesinti Listesi Düzenleyici</h1>', unsafe_allow_html=True)

col_header_left, col_header_right = st.columns([1, 1])

with col_header_right:
    st.markdown("""
<div class="info-box">
    <strong>✨ Özellikler:</strong><br>
    • Sütun eşleştirme ile esnek veri işleme<br>
    • Otomatik Türkçe karakter düzeltme<br>
    • Excel/CSV/TXT format desteği<br>
    • Akıllı sütun algılama ve öneri sistemi
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE İNİT
# -----------------------------------------------------------------------------
if 'step' not in st.session_state:
    st.session_state.step = 1

if 'raw_df' not in st.session_state:
    st.session_state.raw_df = None

if 'column_mapping' not in st.session_state:
    st.session_state.column_mapping = None

if 'clean_df' not in st.session_state:
    st.session_state.clean_df = None

if 'skip_rows' not in st.session_state:
    st.session_state.skip_rows = 0

# -----------------------------------------------------------------------------
# SIDEBAR: İLERLEME TAKİBİ
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎯 İşlem Adımları")
    
    steps = [
        ("1️⃣", "Dosya Yükle", 1),
        ("2️⃣", "Sütun Eşleştir", 2),
        ("3️⃣", "Veriyi İşle", 3),
        ("4️⃣", "İndir", 4)
    ]
    
    for icon, label, step_num in steps:
        if st.session_state.step >= step_num:
            st.markdown(f"**{icon} {label}** ✅")
        else:
            st.markdown(f"{icon} {label}")
    
    st.markdown("---")
    
    # Reset butonu
    if st.button("🔄 Yeni İşlem Başlat", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    st.markdown("**💡 İpucu:**")
    st.caption("Akıllı öneri sistemini kullanarak sütunları otomatik eşleştirebilirsiniz.")

# -----------------------------------------------------------------------------
# ADIM 1: DOSYA YÜKLEME
# -----------------------------------------------------------------------------
st.markdown('<span class="step-badge">Adım 1</span>', unsafe_allow_html=True)
st.markdown("### 📁 Dosya Yükleme")

uploaded_file = st.file_uploader(
    "CSV, Excel veya TXT dosyanızı seçin",
    type=["csv", "xlsx", "txt", "xls"],
    help="Desteklenen formatlar: .csv, .xlsx, .xls, .txt"
)

if uploaded_file is not None:
    
    # İlk yükleme ise
    if st.session_state.raw_df is None:
        
        with st.spinner("📂 Dosya okunuyor ve analiz ediliyor..."):
            try:
                # Önce veri başlangıç satırını otomatik tespit et
                uploaded_file.seek(0)
                auto_skip = find_data_start_row(uploaded_file)
                st.session_state.skip_rows = auto_skip
                
                # Dosyayı oku
                uploaded_file.seek(0)
                st.session_state.raw_df = read_file_with_encoding(uploaded_file, skip_rows=auto_skip)
                st.session_state.step = 2
                
                # Önceki işlemleri sıfırla
                st.session_state.clean_df = None
                
                if auto_skip > 0:
                    st.success(f"✅ Dosya yüklendi! (İlk {auto_skip} satır atlandı, {len(st.session_state.raw_df)} veri satırı, {len(st.session_state.raw_df.columns)} sütun)")
                else:
                    st.success(f"✅ Dosya yüklendi! ({len(st.session_state.raw_df)} satır, {len(st.session_state.raw_df.columns)} sütun)")
                    
            except Exception as e:
                st.error(f"❌ Hata: {e}")
                st.stop()
    
    # -----------------------------------------------------------------------------
    # ADIM 2: SÜTUN EŞLEŞTİRME
    # -----------------------------------------------------------------------------
    if st.session_state.step >= 2:
        st.markdown("---")
        st.markdown('<span class="step-badge">Adım 2</span>', unsafe_allow_html=True)
        
        # Gerekli sütun tanımları
        required_columns = {
            "Üye No": "member_no",
            "Adı": "first_name",
            "Soyadı": "last_name",
            "TC Kimlik No": "tc_no",
            "Aidat Tutarı": "amount"
        }
        
        # Sütun eşleştirme componentini render et
        mapping = render_column_mapper(
            st.session_state.raw_df,
            required_columns
        )
        
        # Eşleştirme geçerli mi kontrol et
        is_valid, missing_fields = validate_mapping(mapping, required_columns)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if not is_valid:
                # Birleşik isim modunda farklı mesaj göster
                use_combined = mapping.get('use_combined_name', False)
                if use_combined:
                    # full_name için özel kontrol
                    missing_display = []
                    for field in missing_fields:
                        if field == 'full_name':
                            missing_display.append('Adı Soyadı (Birleşik)')
                        else:
                            for k, v in required_columns.items():
                                if v == field:
                                    missing_display.append(k)
                                    break
                    st.warning(f"⚠️ Lütfen tüm alanları eşleştirin. Eksik: {', '.join(missing_display)}")
                else:
                    st.warning(f"⚠️ Lütfen tüm alanları eşleştirin. Eksik: {', '.join([k for k, v in required_columns.items() if v in missing_fields])}")
            else:
                if st.button("✨ Veriyi İşle ve Temizle", use_container_width=True, type="primary"):
                    st.session_state.column_mapping = mapping
                    st.session_state.step = 3
                    st.rerun()
    
    # -----------------------------------------------------------------------------
    # ADIM 3: VERİ İŞLEME
    # -----------------------------------------------------------------------------
    if st.session_state.step >= 3 and st.session_state.column_mapping:
        st.markdown("---")
        st.markdown('<span class="step-badge">Adım 3</span>', unsafe_allow_html=True)
        st.markdown("### ⚙️ Veri İşleme")
        
        if st.session_state.clean_df is None:
            with st.spinner("🔄 Veriler işleniyor ve temizleniyor..."):
                try:
                    st.session_state.clean_df, processing_stats = apply_column_mapping(
                        st.session_state.raw_df,
                        st.session_state.column_mapping
                    )
                    st.session_state.processing_stats = processing_stats
                    st.session_state.step = 4
                except Exception as e:
                    st.error(f"❌ İşleme hatası: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    st.stop()
        
        # Sonuç gösterimi
        if st.session_state.clean_df is not None and not st.session_state.clean_df.empty:
            
            # İstatistikler
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Toplam Kayıt", len(st.session_state.clean_df))
            
            with col2:
                total_amount = st.session_state.clean_df['Aidat Tutarı'].sum()
                st.metric("💰 Toplam Tutar", f"{total_amount:,.2f} ₺")
            
            with col3:
                avg_amount = st.session_state.clean_df['Aidat Tutarı'].mean()
                st.metric("📈 Ortalama Tutar", f"{avg_amount:,.2f} ₺")
            
            with col4:
                unique_members = st.session_state.clean_df['TC Kimlik No'].nunique()
                st.metric("👥 Benzersiz Üye", unique_members)
            
            st.markdown("---")
            
            # Temizlenmiş veri tablosu
            st.markdown("### ✅ Temizlenmiş Veri")
            
            # Filtreleme seçenekleri
            col1, col2 = st.columns(2)
            
            with col1:
                search_term = st.text_input("🔍 Ad/Soyad ile ara", placeholder="Örn: Ahmet")
            
            with col2:
                min_amount = st.number_input("💵 Minimum tutar filtresi", min_value=0.0, value=0.0)
            
            # Filtreleme uygula
            filtered_df = st.session_state.clean_df.copy()
            
            if search_term:
                mask = (
                    filtered_df['Adı'].str.contains(search_term, case=False, na=False) |
                    filtered_df['Soyadı'].str.contains(search_term, case=False, na=False)
                )
                filtered_df = filtered_df[mask]
            
            if min_amount > 0:
                filtered_df = filtered_df[filtered_df['Aidat Tutarı'] >= min_amount]
            
            st.dataframe(
                filtered_df,
                use_container_width=True,
                height=400
            )
            
            # -----------------------------------------------------------------------------
            # ADIM 4: İNDİRME
            # -----------------------------------------------------------------------------
            st.markdown("---")
            st.markdown('<span class="step-badge">Adım 4</span>', unsafe_allow_html=True)
            st.markdown("### 📥 İndirme")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            # Excel indirme
            with col1:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name='Temiz Liste')
                    
                    workbook = writer.book
                    worksheet = writer.sheets['Temiz Liste']
                    
                    # Başlık formatı
                    header_format = workbook.add_format({
                        'bold': True,
                        'text_wrap': True,
                        'valign': 'top',
                        'fg_color': '#4F46E5',
                        'font_color': '#FFFFFF',
                        'border': 1
                    })
                    
                    # Başlıkları formatla
                    for col_num, value in enumerate(filtered_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                    
                    # Sütun genişlikleri
                    worksheet.set_column('A:A', 15)  # Üye No
                    worksheet.set_column('B:B', 20)  # Adı
                    worksheet.set_column('C:C', 20)  # Soyadı
                    worksheet.set_column('D:D', 15)  # TC
                    worksheet.set_column('E:E', 15)  # Tutar
                
                st.download_button(
                    label="📊 Excel İndir",
                    data=buffer.getvalue(),
                    file_name=f"SendikaListesi_Temiz_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                    type="primary"
                )
            
            # CSV indirme
            with col2:
                csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📄 CSV İndir",
                    data=csv_data,
                    file_name=f"SendikaListesi_Temiz_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # JSON indirme
            with col3:
                json_data = filtered_df.to_json(orient='records', force_ascii=False, indent=2)
                st.download_button(
                    label="📋 JSON İndir",
                    data=json_data,
                    file_name=f"SendikaListesi_Temiz_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
        else:
            st.error("❌ İşlenebilir veri bulunamadı!")
            
            st.markdown("### 🔍 Olası Nedenler ve Çözümler:")
            
            st.markdown("""
            1. **TC Kimlik No sütunu yanlış seçilmiş olabilir**
               - TC Kimlik No 11 haneli sayısal bir değer olmalıdır
               - Geri dönüp sütun eşleştirmesini kontrol edin
            
            2. **Veri formatı beklenenden farklı olabilir**
               - TC Kimlik boşluk veya özel karakter içeriyor olabilir
               - Dosyanın başından daha fazla satır atlamanız gerekebilir
            
            3. **Tüm satırlar boş olabilir**
               - "Atlanan satır sayısı" değerini azaltmayı deneyin
               - Ham veri önizlemesinde gerçek veriyi gördüğünüzden emin olun
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("⬅️ Sütun Eşleştirmesine Dön", use_container_width=True, type="primary"):
                    st.session_state.step = 2
                    st.session_state.clean_df = None
                    st.rerun()
            
            with col2:
                if st.button("📁 Dosya Yüklemeye Dön", use_container_width=True):
                    st.session_state.step = 1
                    st.session_state.raw_df = None
                    st.session_state.clean_df = None
                    st.session_state.column_mapping = None
                    st.rerun()

else:
    st.info("👆 Başlamak için bir dosya yükleyin")

# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; padding: 2rem;">
    Geliştirici: <a href="https://omersevim.com.tr" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 600;">Osoft</a>
</div>
""", unsafe_allow_html=True)
