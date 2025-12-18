"""
Dışa aktarma işlemleri
"""
import pandas as pd
import io
import streamlit as st
from datetime import datetime


def export_to_excel(df, filename="BMS_Sendika_Temiz.xlsx"):
    """
    DataFrame'i Excel formatında export eder
    
    Args:
        df: Export edilecek DataFrame
        filename: Dosya ismi
        
    Returns:
        BytesIO: Excel dosyası buffer'ı
    """
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Temiz Liste')
        
        workbook = writer.book
        worksheet = writer.sheets['Temiz Liste']
        
        # Başlık formatı (Modern ve renkli)
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#667eea',
            'font_color': 'white',
            'border': 1,
            'font_size': 11
        })
        
        # Veri formatı
        cell_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter'
        })
        
        # Başlıkları yaz
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Kolon genişlikleri
        worksheet.set_column('A:A', 15)  # Üye No
        worksheet.set_column('B:B', 20)  # Adı
        worksheet.set_column('C:C', 20)  # Soyadı
        worksheet.set_column('D:D', 15)  # TC Kimlik
        worksheet.set_column('E:E', 15)  # Tutar
        
        # Satır yüksekliği
        worksheet.set_default_row(20)
    
    buffer.seek(0)
    return buffer


def render_export_section(df):
    """
    Export seçeneklerini render eder
    
    Args:
        df: Export edilecek DataFrame
    """
    st.markdown("### 💾 Dışa Aktarma")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Excel export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"Sendika_Liste_{timestamp}.xlsx"
        
        excel_buffer = export_to_excel(df, excel_filename)
        
        st.download_button(
            label="📥 Excel İndir",
            data=excel_buffer,
            file_name=excel_filename,
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
    
    with col2:
        # CSV export
        csv_filename = f"Sendika_Liste_{timestamp}.csv"
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📄 CSV İndir",
            data=csv_data,
            file_name=csv_filename,
            mime="text/csv",
            use_container_width=True
        )
    
    # İstatistikler
    st.divider()
    st.markdown("#### 📈 Özet İstatistikler")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Toplam Kayıt", len(df))
    
    with col2:
        if "Aidat Tutarı" in df.columns:
            try:
                total_amount = pd.to_numeric(df["Aidat Tutarı"], errors='coerce').sum()
                st.metric("Toplam Aidat", f"{total_amount:,.2f} ₺")
            except:
                st.metric("Toplam Aidat", "N/A")
        else:
            st.metric("Toplam Aidat", "N/A")
    
    with col3:
        if "TC Kimlik No" in df.columns:
            valid_tc = df["TC Kimlik No"].notna().sum()
            st.metric("Geçerli TC", valid_tc)
        else:
            st.metric("Geçerli TC", "N/A")
    
    with col4:
        # Eksik veri oranı
        missing_ratio = (df.isna().sum().sum() / (len(df) * len(df.columns))) * 100
        st.metric("Eksik Veri", f"{missing_ratio:.1f}%")

