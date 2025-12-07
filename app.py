import streamlit as st
import pandas as pd
import re
import io

# -----------------------------------------------------------------------------
# 1. SAYFA AYARLARI
# -----------------------------------------------------------------------------
st.set_page_config(page_title="BMS Sendika Veri Temizleyici", layout="wide")

st.title("?? Sendika Kesinti Listesi Duzenleyici")
st.markdown("""
Bu arac, karma??k CSV/Excel c?kt?lar?n? temizler. 
**11 haneli TC Kimlik Numaras?n?** referans alarak sat?rdaki kaymalar? otomatik duzeltir.
""")

# -----------------------------------------------------------------------------
# 2. VER? TEM?ZLEME FONKS?YONU
# -----------------------------------------------------------------------------
def clean_and_parse_data_v2(file_content):
    data_rows = []
    
    # Sat?rlara bol
    lines = file_content.splitlines()
    
    for line in lines:
        # 1. Ad?m: Sat?rda 11 haneli bir TC Kimlik var m?? (En guvenilir capa noktas?)
        # Regex: Ba??nda veya sonunda ba?ka rakam olmayan tam 11 haneli say?
        tc_match = re.search(r'(?<!\d)\d{11}(?!\d)', line)
        
        if tc_match:
            try:
                tc_value = tc_match.group(0)
                
                # 2. Ad?m: Sat?r? noktal? virgul veya virgulden ay?r
                if ";" in line and "," not in line:
                    parts = line.split(';')
                else:
                    parts = line.split(',')
                
                # 3. Ad?m: Bo?luklar? temizle ve sadece DOLU verileri bir listeye al
                # Ornek: ['1', '', '', 'Ahmet', '', 'Y?lmaz', '12345678901', '', '300.50'] 
                # Donu?ur -> ['1', 'Ahmet', 'Y?lmaz', '12345678901', '300.50']
                clean_parts = [p.strip() for p in parts if p.strip()]
                
                # TC Kimlik Numaras?n?n bu temiz listedeki yerini (index) bul
                try:
                    tc_index = clean_parts.index(tc_value)
                except ValueError:
                    continue # Listede bulamazsa atla

                # 4. Ad?m: TC'nin konumuna gore SA? ve SOL verileri ata
                # Mant?k: [..., Ad, Soyad, TC, Tutar, ...]
                
                # Tutar (TC'den hemen sonraki eleman)
                tutar = "0"
                if len(clean_parts) > tc_index + 1:
                    tutar = clean_parts[tc_index + 1]
                
                # Soyad? (TC'den hemen onceki eleman)
                soyadi = ""
                if tc_index > 0:
                    soyadi = clean_parts[tc_index - 1]
                
                # Ad? (Soyad?ndan onceki eleman)
                adi = ""
                if tc_index > 1:
                    # Genellikle Soyad?n?n hemen solu Add?r.
                    adi = clean_parts[tc_index - 2]
                
                # Uye No (Ad'dan onceki eleman - e?er varsa)
                uye_no = ""
                if tc_index > 2:
                    uye_no = clean_parts[tc_index - 3]
                else:
                    # E?er liste k?saysa (S?ra no yoksa), ilk eleman uye no olabilir
                    uye_no = clean_parts[0] if tc_index > 0 else ""

                # Veriyi sozluk olarak kaydet
                row_dict = {
                    "Uye No": uye_no,
                    "Ad?": adi,
                    "Soyad?": soyadi,
                    "TC Kimlik No": tc_value,
                    "Aidat Tutar?": tutar
                }
                data_rows.append(row_dict)
                
            except Exception as e:
                # Hata olursa konsola yaz ama program? durdurma
                print(f"Sat?r i?lenirken hata: {e}")
                continue

    return pd.DataFrame(data_rows)

# -----------------------------------------------------------------------------
# 3. ARAYUZ VE DOSYA YUKLEME
# -----------------------------------------------------------------------------

# BURASI GUNCELLEND?: "xls" eklendi.
uploaded_file = st.file_uploader("Dosyay? Yukle", type=["csv", "xlsx", "txt", "xls"])

if uploaded_file is not None:
    st.info("Dosya analiz ediliyor...")
    
    string_data = ""
    
    # --- Dosya Okuma ve Kodlama Cozme ---
    try:
        # Excel dosyalar? (xlsx veya xls)
        if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            try:
                # Excel'i pandas ile oku
                df_temp = pd.read_excel(uploaded_file, header=None, dtype=str)
                # ??lenebilmesi icin CSV format?nda string'e cevir
                string_data = df_temp.to_csv(index=False, header=False)
            except Exception as excel_error:
                st.error(f"Excel dosyas? okunamad?: {excel_error}")
        
        # Metin tabanl? dosyalar (csv veya txt)
        else:
            raw_bytes = uploaded_file.getvalue()
            
            # Kodlama (Encoding) Denemeleri
            # 1. Turkce Windows format? (Genelde bu cal???r)
            try:
                string_data = raw_bytes.decode("cp1254")
            except UnicodeDecodeError:
                # 2. Standart UTF-8
                try:
                    string_data = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    # 3. Latin-1 (Son care)
                    string_data = raw_bytes.decode("latin-1")
        
        # --- Temizleme Fonksiyonunu Cal??t?r ---
        if string_data:
            df_clean = clean_and_parse_data_v2(string_data)
            
            if not df_clean.empty:
                st.success(f"Ba?ar?l?! Toplam {len(df_clean)} ki?i listelendi.")
                
                # Tabloyu Goster
                st.dataframe(df_clean)
                
                # Excel ?ndirme Butonu Haz?rla
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_clean.to_excel(writer, index=False, sheet_name='Temiz Liste')
                    # Sutun geni?liklerini ayarla
                    worksheet = writer.sheets['Temiz Liste']
                    worksheet.set_column('A:E', 20)

                st.download_button(
                    label="?? Temizlenmi? Excel Olarak ?ndir",
                    data=buffer,
                    file_name="BMS_Sendika_Temiz_Liste.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.error("Veri bulunamad?. Dosya iceri?inde TC Kimlik No (11 hane) oldu?undan emin olun.")
                st.text("Dosyadan okunan ilk k?s?m:")
                st.text(string_data[:500])

    except Exception as e:
        st.error(f"Beklenmeyen bir hata olu?tu: {e}")