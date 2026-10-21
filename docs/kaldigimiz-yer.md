# Kaldığımız yer

**21/10/2026, 16:57.** 2. adım (siparişler) kullanıcının düzeltmeleriyle tamamlandı; 3a (iş emirlerinin yüklenmesi ve siparişe bağlanması) başlıyor.

## Bu oturumda yapılanlar

- 2. adım: ERP yükleme ekranı, sipariş talepleri listesinin işlenmesi, sipariş kartları.
  - ERP okuyucu (`erp_okuyucu.py`): .xls/.xlsx.
  - Eşleştirici (`erp_aktarim.py`).
  - Ürün kuralları (`urun_kurallari.py`).
- Siparişler ekranı: Gecikenler, 14 gün içinde, Planlananlar ve en sağda Onay bekleyen projeler sütunları.
  - Süzgeçler ve arama var.
  - Ürün kutucukları aile rengini taşır; tıklanınca sipariş kartında o ailenin bölümüne gider.
- Özet (ana ekran):
  - Tıklanır sayı kutuları.
  - Makinelerin aileye ve planlama durumuna göre pastaları.
  - Haftalık teslim takvimi.
  - Teslimi geçen ve yaklaşan siparişler tablosu (satırın tamamı tıklanır).
  - Kart başlıkları büyük harfli.
- Sevk edilecek makineler sayfası (`makineler.py`):
  - Pastalar, takvim ve "Sevk edilecek ürün" kutusu bu sayfayı açar.
  - Makineler proje proje listelenir; planlama durumuna göre seçilir.
- Onay bekleyen siparişler sevk edilecek, teslim ve açık sipariş sayılarına girmez.
- Sipariş talebi revizyonları: her yüklemede değişen alanlar kaydedilir; sipariş kartında tablo ve "Revize edildi" etiketi.
- Seri no'su olmayan OVF ve WD satırları makine sayılmaz (göç 5 mevcut kayıtları da düzeltir).
- Sevkiyat (çeyrek dönemler) ve Yedek parça ekranları.
- Kurallar:
  - En son yüklenen ERP listesi gerçeği gösterir.
  - Aynı satırın iptal ve geçerli kaydı varsa geçerli olan alınır.
  - "OZ" + rakam kodlu kalemler dış tedariktir.
- Görünüm:
  - Müşteri markası: sipariş kutusunun üzerine gelince müşterinin rengi ve logosu görünür. Tanımlı olmayan müşterilerde OMS logosu ve OMS kırmızısı kullanılır.
  - Özet kutularında OMS logosu filigranı.
- 77 otomatik test geçiyor.

## Sıradaki iş

1. 3a: açık ve kapalı iş emirlerinin yüklenmesi, siparişe kendiliğinden bağlanması (sipariş satırındaki "Bağlı İşemri No", iş emri açıklamasındaki proje kodu, "Sip. No"), sipariş kartında gösterilmesi, "Malzeme hazırlık" geçişi; ardından bağlanamayanların kullanıcıya sorulması.
2. 3b: ürün sayfası (iş emrinin kırılımları: tamamlanan ve bekleyen).
3. 3c: çıkış yapılamayan malzeme, "İş emri tamamlandı ama ERP'de İmalatta" uyarısı, Yapılacaklar listesi.
4. Ardından test → motor açılışı → eksper → metal etiket sırası (4. adımla birlikte).

## Kullanıcıdan beklenenler

- `baslat.bat`'ı yeniden açmak (göç 5 açılışta uygulanır).
- 3. adım için ERP'den güncel açık ve kapalı iş emirleri listeleri.
- Sunucu yedeği kullanıcı kararıyla ertelendi. `OMS Veri` şimdilik yalnızca bu bilgisayarda; yedek klasörü seçilince `yedek-hedefi.txt` yazılır.
