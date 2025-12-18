# 📊 Sendika Kesinti Listesi Düzenleyici

Modern, kullanıcı dostu ve güvenli veri temizleme uygulaması. Karmaşık CSV/Excel dosyalarını kolayca temizler ve düzenler.

## ✨ Özellikler

- **🔄 Esnek Sütun Eşleştirme**: Dosyanızdaki sütunları istediğiniz alanlara manuel veya otomatik eşleştirin
- **🤖 Akıllı Öneri Sistemi**: Sütun isimlerine göre otomatik eşleştirme önerileri
- **🌍 Türkçe Karakter Desteği**: Bozuk encoding'lerden kaynaklı karakter hatalarını otomatik düzeltir
- **📁 Çoklu Format Desteği**: CSV, Excel (xlsx/xls), TXT dosyalarını okur
- **📊 Detaylı İstatistikler**: Toplam tutar, ortalama, kayıt sayısı gibi metrikler
- **🔍 Filtreleme**: Ad/soyad araması ve minimum tutar filtreleme
- **📥 Çoklu Export**: Excel, CSV ve JSON formatlarında indirme

## 🚀 Kurulum

### Gereksinimler
- Python 3.8 veya üzeri

### Adımlar

1. **Bağımlılıkları yükleyin:**
```bash
pip install -r requirements.txt
```

2. **Uygulamayı başlatın:**
```bash
streamlit run app.py
```

3. **Tarayıcınızda açılacak adresi ziyaret edin:**
```
http://localhost:8501
```

## 📖 Kullanım

### Adım 1: Dosya Yükleme
- CSV, Excel veya TXT dosyanızı sürükle-bırak yapın veya seçin

### Adım 2: Sütun Eşleştirme
- Ham verinizin önizlemesini görün
- Her alanı (Üye No, Ad, Soyad, TC, Tutar) dosyanızdaki uygun sütunla eşleştirin
- **💡 İpucu:** "Akıllı Öneri" özelliğini kullanarak otomatik eşleştirme yapabilirsiniz

### Adım 3: Veri İşleme
- "Veriyi İşle ve Temizle" butonuna tıklayın
- Temizlenmiş veriyi görüntüleyin
- İstatistikleri inceleyin
- Gerekirse filtreleyin

### Adım 4: İndirme
- Excel, CSV veya JSON formatında indirin

## 📁 Proje Yapısı

```
cevirici/
├── app.py                      # Ana uygulama dosyası
├── components/
│   └── column_mapper.py        # Sütun eşleştirme UI componenti
├── utils/
│   └── data_processor.py       # Veri işleme fonksiyonları
├── data/
│   └── ornek_veri.csv         # Örnek test verisi
├── requirements.txt           # Python bağımlılıkları
└── README.md                  # Dokümantasyon
```

## 🧪 Test Verisi

`data/ornek_veri.csv` dosyasında test için hazır örnek veri bulunmaktadır.

## 🔒 Güvenlik

- ✅ SQL Injection koruması (pandas kullanılıyor, doğrudan SQL yok)
- ✅ XSS koruması (Streamlit otomatik escape ediyor)
- ✅ Dosya tipi doğrulama
- ✅ Hata yakalama ve güvenli işleme
- ✅ Kullanıcı verisi sunucuda saklanmaz (session state kullanımı)

## 🛠️ Teknolojiler

- **Streamlit** 1.32.0 - Modern web arayüzü
- **Pandas** 2.0.0 - Veri işleme
- **OpenPyXL** 3.1.2 - Excel okuma
- **XlsxWriter** 3.1.9 - Excel yazma

## 📝 Notlar

- Dosyalar otomatik encoding tespiti ile okunur (cp1254, utf-8, iso-8859-9, latin-1)
- TC Kimlik numarası 11 hane olmalıdır
- Tutar değerleri otomatik olarak virgülden noktaya çevrilir
- Bozuk Türkçe karakterler otomatik düzeltilir

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Commit yapın (`git commit -am 'Yeni özellik eklendi'`)
4. Push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request açın

## 📄 Lisans

Bu proje kişisel kullanım içindir.

---

**Not:** Herhangi bir sorun için issue açabilir veya doğrudan iletişime geçebilirsiniz.

