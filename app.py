import streamlit as st
import pandas as pd
import re
import io

# Sayfa Ayarlar?
st.set_page_config(page_title="BMS Sendika Veri Temizleyici V2", layout="wide")

st.title("?? Sendika Kesinti Listesi Duzenleyici (V2)")
st.markdown("""
**Hata Giderilmi? Versiyon:**
Bu arac, dosya kodlamas?n? (TR karakterleri) otomatik alg?lar ve bo?luklardan etkilenmeden
TC Kimlik numaras?n? referans alarak veriyi ceker.
""")

def clean_and_parse_data_v2(file_content):
    data_rows = []
    
    # Sat?rlara bol
    lines = file_content.splitlines()
    
    debug_count = 0
    
    for line in lines:
        # 1. Ad?m: Sat?rda 11 haneli bir TC Kimlik var m?? (En guvenilir capa noktas?)
        # Regex: Ba??nda veya sonunda say? olmayan tam 11 haneli say?
        tc_match = re.search(r'(?<!\d)\d{11}(?!\d)', line)
        
        if tc_match:
            try:
                tc_value = tc_match.group(0)
                
                # 2. Ad?m: Sat?r? virgullerden (veya noktal? virgulden) ay?r
                # Excel bazen ; bazen , kullan?r. ?kisini de garantiye alal?m.
                if ";" in line and "," not in line:
                    parts = line.split(';')
                else:
                    parts = line.split(',')
                
                # 3. Ad?m: Bo?luklar? temizle ve sadece dolu verileri bir listeye al
                # Ornek donu?um: ['1', '', '', 'Ahmet', '', 'Y?lmaz', '123...', ''] 
                # -> ['1', 'Ahmet', 'Y?lmaz', '123...']
                clean_parts = [p.strip() for p in parts if p.strip()]
                
                # TC Kimlik Numaras?n?n bu temiz listedeki yerini bul
                try:
                    tc_index = clean_parts.index(tc_value)
                except ValueError:
                    continue # Listede bulamazsa atla

                # 4. Ad?m: TC'ye gore sa? ve solu ata
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
                    # Bazen ad iki kelime olabilir, veya ba??nda Uye No olabilir.
                    # Genellikle Soyad?n?n hemen solu Add?r.
                    adi = clean_parts[tc_index - 2]
                
                # Uye No (Ad'dan onceki eleman - e?er varsa)
                uye_no = ""
                if tc_index > 2:
                    uye_no = clean_parts[tc_index - 3]
                else:
                    # E?er liste k?saysa (S?ra no yoksa), ilk eleman uye no olabilir
                    uye_no = clean_parts[0] if tc_index > 0 else ""

                # E?er "Ad?" sutununa say? geldiyse (bazen s?ra kayabilir), duzelt
                # (?ste?e ba?l? kontrol)

                # Listeye ekle
                row_dict = {
                    "Uye No": uye_no,
                    "Ad?": adi,
                    "Soyad?": soyadi,
                    "TC Kimlik No": tc_value,
                    "Aidat Tutar?": tutar
                }
                data_rows.append(row_dict)
                
            except Exception as e:
                print(f"Sat?r i?lenirken hata: {e}")
                continue

    return pd.DataFrame(data_rows)

# --- Arayuz K?sm? ---

uploaded_file = st.file_uploader("Dosyay? Yukle (CSV veya Excel)", type=["csv", "xlsx", "txt"])

if uploaded_file is not None:
    st.info("Dosya analiz ediliyor...")
    
    string_data = ""
    
    # --- Dosya Okuma ve Kodlama Cozme ---
    try:
        if uploaded_file.name.endswith('.xlsx'):
            # Excel dosyas?
            df_temp = pd.read_excel(uploaded_file, header=None, dtype=str)
            # CSV format?na cevir (virgulle ayr?lm?? string)
            string_data = df_temp.to_csv(index=False, header=False)
        else:
            # CSV veya TXT dosyas?
            raw_bytes = uploaded_file.getvalue()
            
            # Once Turkce karakter seti (cp1254) dene, Excel genelde bunu kullan?r
            try:
                string_data = raw_bytes.decode("cp1254")
            except UnicodeDecodeError:
                # Olmazsa utf-8 dene
                try:
                    string_data = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    # O da olmazsa latin-1 dene (son care)
                    string_data = raw_bytes.decode("latin-1")
        
        # --- Temizleme Fonksiyonunu Cal??t?r ---
        df_clean = clean_and_parse_data_v2(string_data)
        
        if not df_clean.empty:
            st.success(f"Ba?ar?l?! Toplam {len(df_clean)} ki?i listelendi.")
            
            # Veri Onizleme
            st.dataframe(df_clean)
            
            # Excel ?ndirme
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_clean.to_excel(writer, index=False, sheet_name='Temiz Liste')
                worksheet = writer.sheets['Temiz Liste']
                worksheet.set_column('A:E', 20)

            st.download_button(
                label="?? Excel Olarak ?ndir",
                data=buffer,
                file_name="Temizlenmis_Sendika_Listesi.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.error("Veri bulunamad?. Dosya iceri?i beklenenden cok farkl? olabilir.")
            st.warning("?pucu: Dosyan?n icinde 11 haneli TC Kimlik numaralar? oldu?undan emin olun.")
            # Hata ay?klama icin ilk 5 sat?r? goster
            st.text("Dosyadan okunan ilk 5 sat?r (kontrol icin):")
            st.text(string_data[:500])

    except Exception as e:
        st.error(f"Kritik Hata: {e}")