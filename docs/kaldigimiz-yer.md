# Kaldığımız yer

**03/11/2026, 18:00.** Siparişler ekranı Planner gibi aşama sütunlu bir pano oldu; stoktaki makineler (planın 5. adımından öne alındı), daralan sol menü ve yeni alev yapıldı. Kullanıcı 04/11/2026'da deneyecek.

## Bu oturumda yapılanlar

- Siparişler ekranı Planner gibi pano:
  - 5 sütun: Siparişler, Sevke hazır / Stok, Son montaj & test, Montajı devam edenler, Malzeme hazırlık. Sevk edilenler ve onay bekleyenler altta kapalı bölümlerde.
  - Kartta etiketler (model, asıl aşama, KCN/SCN/ACN çeneleri, Sipariş, Sıcak sipariş, Stok); etikete tıklayınca süzülür, birden çok etiket birlikte seçilir.
  - Aşama kartın sağ üstündeki düğmeyle değişiyor; geri alırken sebep soruluyor, çıktı kuralı geçerli.
  - Sıcak sipariş (talepten teslime 30 gün ya da daha az): etikette alev simgesi, kartın altında turuncu çizgi, üzerine gelince yükselen alevler.
- Kişiler: varsayılan atama (Kullanıcılar ekranından seçiliyor), kartta baş harfler ya da fotoğraf; kişinin görevi ve rengi.
- Sipariş kartı: başlıkta makine başına bir satır (model, iş emri, yağ ya da renk; PP ve SVR'de "Standart" RAL3020); ürün satırları üç düzenli satır.
- "İmalatta" sorusu kalktı; fark kartta yalnızca bilgi olarak görünüyor.
- Sol menü logonun yanındaki düğmeyle daralıp genişliyor; üzerine gelince açılmıyor, seçim hatırlanıyor.
- Stoktaki makineler (göç 18):
  - Sevk deposu ve montaj üretim deposu raporlarından; depodaki adetten açık siparişlere ait olanlar düşülüp kalan kadar "Stok" kartı açılıyor. Depo dosya adından anlaşılıyor.
  - Makineler panoda "Sevke hazır / Stok" sütununda; çene ve kiriş Stok ekranında.
  - Sevk deposundaki makine test edilmiş sayılıyor; montaj üretim deposundaki için "Testi yapıldı mı?" soruluyor.
  - Stok iş emri karta kendiliğinden bağlanıyor. Siparişe atanınca numaralar, notlar ve iş emri siparişin kartına geçiyor; ERP'de siparişe bağlanan stok kendiliğinden atanıyor.
  - Stok makinesi elle eklenebiliyor, sebep seçilerek stoktan çıkarılabiliyor. OVF ve WD'de yalnızca daha önce makine olarak geçmiş kodlar kendiliğinden kart oluyor.
- Ürün sayfasında aşama değiştirince Özet'e dönme hatası düzeldi.
- 142 otomatik test geçiyor; gerçek verinin kopyasında 910 sayfa hatasız açılıyor.

## Sıradaki iş

1. Kullanıcının denemesi: açık bütün `baslat.bat` pencereleri kapatılıp yeniden açılır (göç 18 çalışır). Güncel sevk depo ve montaj üretim depo stok raporları birlikte yüklenir; Stok ekranı, panodaki stok kartları, test sorusu ve siparişe atama denenir. Menü düğmesi ve alev görülür (alev beğenilmezse kaldırılır).
2. 4. adımın kalan parçaları, her biri önce sorularla: kontrol listesi ve PP şablonu, fotoğraf, kart kart atama ve etiketler. Pano parçası Siparişler panosuyla yapıldı.
3. Stok test sorusunun Yapılacaklar'a eklenmesi (isteğe bağlı) ve Yapılacaklar'ın sadeleştirilmesi: kullanıcıya hâlâ karışık geliyor.
4. SVR ve OVR formları (test formu ve montaj öncesi kalite kontrol formları): kullanıcı hazır olunca.
5. ERP'den canlı veri (API, 15 dakikada bir): ERP sorumlusundan adres, belge ve salt okunur erişim gelince.

## Kullanıcıdan beklenenler

- Yeni ekranları denemek; stok kartlarına numaraları girmek, montaj üretim deposundakilerin testini cevaplamak; ERP'de bulunamayan stok makinelerini (OVF, WD, eski makineler) elle eklemek.
- Proje takip kartının son hâlini onaylamak (örnekler `OMS Veri/taslaklar/`).
- PP-908'in test öncesi kontrol formunu ve 9XX test formunu hazırlanınca `OMS Veri/uygulama/formlar/` klasörüne koymak; o zamana kadar PP-908'de çıktı alınamaz.
- ERP'deki hatalı ve boş yarı mamul rotalarını güncellemek.
- "Makine numaraları" şablonunu doldurup yüklemek (şasi no'lar; iki motorlu PP'lerde ikinci motor).
- Asistan: Anthropic'in iade cevabı gelince denemeye karar vermek.
- ERP sorumlusundan: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
