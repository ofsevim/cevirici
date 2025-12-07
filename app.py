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
        # 1. Ad?m: Sat?rda 11 haneli bir TC Kimlik var m??
        tc_match = re.search(r'(?<!\d)\d{11}(?!\d)', line)
        
        if tc_match:
            try:
                tc_value = tc_match.group(0)
                
                # 2. Ad?m: Sat?r? noktal? virgul veya virgulden ay?r
                # Oncelik noktal? virgulde (Excelden donu?tururken bunu kullanaca??z)
                if ";" in line:
                    parts = line.split(';')
                else:
                    parts = line.split(',')
                
                # 3. Ad?m: Bo?luklar? temizle ve sadece DOLU verileri al
                clean_parts = [p.strip() for p in parts if p.strip()]
                
                # TC Kimlik Numaras?n?n konumunu bul
                try:
                    tc_index = clean_parts.index(tc_value)
                except ValueError:
                    continue 

                # 4. Ad?m: Verileri Ata (TC Konumuna Gore)
                
                # --- TUTAR DUZELTME KISMI (BURASI GUNCELLEND?) ---
                tutar = "0"
                if len(clean_parts) > tc_index + 1:
                    raw_tutar = clean_parts[tc_index + 1]
                    
                    # T?rnak i?aretlerini temizle ("293" -> 293)
                    raw_tutar = raw_tutar.replace('"', '').replace("'", "")
                    
                    # Virgulu noktaya cevir (254,14 -> 254.14) ki Excel say? sans?n
                    tutar = raw_tutar.replace(',', '.')
                # -------------------------------------------------
                
                # Soyad?
                soyadi = ""
                if tc_index > 0:
                    soyadi = clean_parts[tc_index - 1]
                
                # Ad?
                adi = ""
                if tc_index > 1:
                    adi = clean_parts[tc_index - 2]
                
                # Uye No
                uye_no = ""
                if tc_index > 2:
                    uye_no = clean_parts[tc_index - 3]
                else:
                    uye_no = clean_parts[0] if tc_index > 0 else ""

                row_dict = {
                    "Uye No": uye_no,
                    "Ad?": adi,
                    "Soyad?": soyadi,
                    "TC Kimlik No": tc_value,
                    "Aidat Tutar?": tutar
                }
                data_rows.append(row_dict)
                
            except Exception as e:
                print(f"Sat?r hatas?: {e}")
                continue

    # DataFrame olu?tur ve Tutar? Say?ya Cevir
    df = pd.read_json(io.StringIO(pd.DataFrame(data_rows).to_json(orient='records')))
    
    # Son olarak Aidat Tutar?n? float (say?) yapmaya cal??, olmuyorsa string kals?n
    try:
        df["Aidat Tutar?"] = pd.to_numeric(df["Aidat Tutar?"])
    except:
        pass

    return df

# -----------------------------------------------------------------------------
# 3. ARAYUZ VE DOSYA YUKLEME
# -----------------------------------------------------------------------------

uploaded_file = st.file_uploader("Dosyay? Yukle", type=["csv", "xlsx", "txt", "xls"])

if uploaded_file is not None:
    st.info("Dosya analiz ediliyor...")
    
    string_data = ""
    
    try:
        # Excel dosyalar? (xlsx veya xls)
        if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            try:
                # Excel'i oku
                df_temp = pd.read_excel(uploaded_file, header=None, dtype=str)
                
                # --- KR?T?K DUZELTME ---
                # CSV'ye cevirirken ay?r?c?y? noktal? virgul (;) yap?yoruz.
                # Boylece say? icindeki virguller (254,14) sutunlar? bolmez.
                string_data = df_temp.to_csv(index=False, header=False, sep=';')
                
            except Exception as excel_error:
                st.error(f"Excel dosyas? okunamad?: {excel_error}")
        
        # Metin tabanl? dosyalar
        else:
            raw_bytes = uploaded_file.getvalue()
            try:
                string_data = raw_bytes.decode("cp1254")
            except UnicodeDecodeError:
                try:
                    string_data = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    string_data = raw_bytes.decode("latin-1")
        
        # --- Temizleme Fonksiyonunu Cal??t?r ---
        if string_data:
            df_clean = clean_and_parse_data_v2(string_data)
            
            if not df_clean.empty:
                st.success(f"Ba?ar?l?! Toplam {len(df_clean)} ki?i listelendi.")
                
                st.dataframe(df_clean)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_clean.to_excel(writer, index=False, sheet_name='Temiz Liste')
                    worksheet = writer.sheets['Temiz Liste']
                    worksheet.set_column('A:E', 20)

                st.download_button(
                    label="?? Temizlenmi? Excel Olarak ?ndir",
                    data=buffer,
                    file_name="BMS_Sendika_Temiz_Liste.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.error("Veri bulunamad?. ?cerikte 11 haneli TC Kimlik No oldu?undan emin olun.")
                st.text("Okunan veri orne?i:")
                st.text(string_data[:500])

    except Exception as e:
        st.error(f"Beklenmeyen bir hata olu?tu: {e}")