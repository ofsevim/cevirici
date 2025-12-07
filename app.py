import streamlit as st
import pandas as pd
import re
import io

# Sayfa Ayarlar?
st.set_page_config(page_title="BMS Sendika Veri Temizleyici", layout="wide")

st.title("?? Sendika Kesinti Listesi Duzenleyici")
st.markdown("""
Bu arac, **Buro Memurlar? Sendikas?** karma??k CSV/Excel c?kt?lar?n? temizleyip
tek ve duzgun bir Excel tablosuna donu?turur.
""")

def clean_and_parse_data(file_content):
    """
    Veriyi sat?r sat?r okur, TC Kimlik No (11 hane) iceren sat?rlar? yakalar
    ve virgullerden ar?nd?rarak temiz bir liste olu?turur.
    """
    data_rows = []
    
    # Dosya iceri?ini sat?rlara bol
    lines = file_content.split('\n')
    
    for line in lines:
        # Sat?rda 11 haneli bir say? var m? kontrol et (TC Kimlik No)
        # Regex: \d{11} -> Yan yana 11 rakam arar
        tc_match = re.search(r'\b\d{11}\b', line)
        
        if tc_match:
            # Sat?r? virgullerden ay?r
            parts = line.split(',')
            
            # Bo?luklar? ve bo? stringleri temizle
            cleaned_parts = [p.strip() for p in parts if p.strip()]
            
            # Temizlenmi? listede en az 5 eleman olmal? (S?ra, UyeNo, Ad, Soyad, TC, Tutar)
            # Bazen S?ra No olmayabilir, bu yuzden esnek davranaca??z.
            if len(cleaned_parts) >= 4:
                try:
                    # Strateji: TC Kimlik Numaras?n? bul ve di?erlerini ona gore konumland?r.
                    # Listede TC'nin indexini bul
                    tc_value = tc_match.group(0)
                    
                    # Listede TC de?erinin tam olarak hangi indexte oldu?unu bulal?m
                    # Bazen TC string icinde ba?ta/sonda bo?lukla gelebilir, match ile garantiye alal?m.
                    tc_index = -1
                    for i, part in enumerate(cleaned_parts):
                        if part == tc_value:
                            tc_index = i
                            break
                    
                    if tc_index != -1:
                        # Tutar: TC'den hemen sonraki elemand?r.
                        tutar = cleaned_parts[tc_index + 1] if (tc_index + 1) < len(cleaned_parts) else "0"
                        
                        # Soyad?: TC'den hemen onceki elemand?r.
                        soyadi = cleaned_parts[tc_index - 1]
                        
                        # Ad?: Soyad?ndan onceki elemand?r. 
                        # Ancak bazen "?ki ?simli" ki?iler olabilir. 
                        # Uye No ile Soyad? aras?ndaki her ?ey "AD"d?r.
                        
                        # Uye No: Genellikle en ba?taki de?il, ondan sonraki say?d?r (En ba? SIRA NO'dur).
                        # Ancak bazen SIRA NO okunmaz.
                        # Genellikle TC indexinden geriye do?ru 3. veya 4. eleman Uye No'dur.
                        
                        # Basit mant?k: 
                        # cleaned_parts genelde ?oyledir: ['1', '287676', 'Seyhan', 'Abca', '25250132516', '325.51']
                        # Index:            0 (S?ra)   1 (Uye)    2 (Ad)    3 (Soyad) 4 (TC)        5 (Tutar)
                        
                        uye_no = cleaned_parts[tc_index - 3] if (tc_index - 3) >= 0 else cleaned_parts[0]
                        
                        # ?sim bulma mant???: Uye No indexi ile Soyad? indexi aras?ndakileri birle?tir
                        uye_no_index = -1
                        # Uye nosunu bulmaya cal??al?m (TC'den once say?sal olan ilk de?er de?il, soyad?ndan once gelen isimlerden onceki say?)
                        # Manuel indexleme daha guvenli bu format icin:
                        
                        # Senaryo 1: S?ra No VAR
                        if tc_index >= 4: 
                            uye_no = cleaned_parts[1] # Genelde 1. index
                            # Ad, index 2'den Soyad indexine kadar olan k?s?md?r
                            adi_list = cleaned_parts[2 : tc_index - 1] 
                            adi = " ".join(adi_list)
                            
                        # Senaryo 2: S?ra No YOK veya hatal? parse edildi
                        elif tc_index == 3: # ['UyeNo', 'Ad', 'Soyad', 'TC', 'Tutar']
                            uye_no = cleaned_parts[0]
                            adi = cleaned_parts[1]
                        
                        else:
                            # Cok istisnai durum, manuel atama deneyelim
                            uye_no = cleaned_parts[1] if len(cleaned_parts) > 1 else ""
                            adi = "Bilinmiyor"

                        # Veriyi kaydet
                        row_dict = {
                            "Uye No": uye_no,
                            "Ad?": adi,
                            "Soyad?": soyadi,
                            "TC Kimlik No": tc_value,
                            "Aidat Tutar?": tutar
                        }
                        data_rows.append(row_dict)
                except Exception as e:
                    # Hatal? sat?r olursa atla ama konsola bas
                    print(f"Hata olu?an sat?r: {cleaned_parts} - Hata: {e}")
                    continue

    return pd.DataFrame(data_rows)

# --- Streamlit Arayuzu ---

uploaded_file = st.file_uploader("Dosyay? Yukle (CSV veya Excel)", type=["csv", "xlsx", "txt"])

if uploaded_file is not None:
    st.info("Dosya i?leniyor...")
    
    # Dosya turune gore okuma
    string_data = ""
    
    try:
        if uploaded_file.name.endswith('.csv') or uploaded_file.name.endswith('.txt'):
            # Byte'? stringe cevir (utf-8 tr karakter deste?i icin onemli)
            string_data = uploaded_file.getvalue().decode("utf-8")
        elif uploaded_file.name.endswith('.xlsx'):
            # Excel ise once pandas ile okuyup csv string format?na cevirelim ki parser cal??s?n
            df_temp = pd.read_excel(uploaded_file)
            string_data = df_temp.to_csv(index=False)
            
        # Temizleme Fonksiyonunu Cal??t?r
        df_clean = clean_and_parse_data(string_data)
        
        if not df_clean.empty:
            st.success(f"??lem Tamamland?! Toplam {len(df_clean)} ki?i bulundu.")
            
            # Tabloyu goster
            st.dataframe(df_clean)
            
            # ?ndirme Butonu (Excel olarak)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_clean.to_excel(writer, index=False, sheet_name='Sendika Listesi')
                
                # Sutun geni?liklerini ayarla (Opsiyonel estetik)
                worksheet = writer.sheets['Sendika Listesi']
                worksheet.set_column('A:A', 15) # Uye No
                worksheet.set_column('B:C', 20) # Ad Soyad
                worksheet.set_column('D:D', 15) # TC
                worksheet.set_column('E:E', 15) # Tutar

            st.download_button(
                label="?? Temizlenmi? Excel'i ?ndir",
                data=buffer,
                file_name="BMS_Sendika_Temiz_Liste.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.error("Veri bulunamad? veya format cok bozuk.")
            
    except Exception as e:
        st.error(f"Bir hata olu?tu: {e}")
        st.warning("Lutfen dosyan?n CSV format?nda oldu?undan veya Excel ise okunabilir oldu?undan emin olun.")