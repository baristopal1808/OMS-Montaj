# Kaldığımız yer

**21/10/2026, 16:35.** 2. adım (siparişler) kullanıcının düzeltmeleriyle tamamlandı; sırada 3. adım (iş emirleri) var.

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
- Sevkiyat (çeyrek dönemler) ve Yedek parça ekranları.
- Kurallar:
  - En son yüklenen ERP listesi gerçeği gösterir.
  - Aynı satırın iptal ve geçerli kaydı varsa geçerli olan alınır.
  - "OZ" + rakam kodlu kalemler dış tedariktir.
- Görünüm:
  - Müşteri markası: sipariş kutusunun üzerine gelince müşterinin rengi ve logosu görünür. Tanımlı olmayan müşterilerde OMS logosu ve OMS kırmızısı kullanılır.
  - Özet kutularında OMS logosu filigranı.
- 73 otomatik test geçiyor.

## Sıradaki iş

1. 3. adım, yavaş yavaş:
   - Açık ve kapalı iş emirlerinin yüklenmesi ve siparişe bağlanması.
   - Ürüne tıklayınca ürün sayfası: iş emri durumu, kırılımlar (tamamlanan ve bekleyen), eksik malzeme.
   - "İş emri tamamlandı ama ERP'de İmalatta" uyarısı (`ihtiyaclar.md`, Kararlar).
   - Yapılacaklar listesi.
2. Ardından test → motor açılışı → eksper → metal etiket sırası (4. adımla birlikte).

## Kullanıcıdan beklenenler

- `baslat.bat`'ı yeniden açıp süzgeçsiz sipariş listesini yeniden yüklemek. İptal satırı düzeltmesi ancak böyle ekrana yansır.
- 3. adım için ERP'den güncel açık ve kapalı iş emirleri listeleri.
- Sunucu yedeği kullanıcı kararıyla ertelendi. `OMS Veri` şimdilik yalnızca bu bilgisayarda; yedek klasörü seçilince `yedek-hedefi.txt` yazılır.
