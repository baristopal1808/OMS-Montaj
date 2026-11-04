# Kaldığımız yer

**04/11/2026, 14:51.** Kullanıcının stok denemesinden çıkan düzeltmeler, karanlık tema ve büyüyen MONTAJ yazısı yapıldı; kullanıcının denemesini bekliyor.

## Bu oturumda yapılanlar

- Stok düzeltmeleri (kullanıcının denemesinden; göç 19):
  - Elle eklenen stok makinesi, depo raporu onu başka depoda gösterse de onunla eşleşiyor; ikinci kart açılmıyor. Mevcut 6 çift kart temizlendi (önce veritabanı yedeklendi); motor seri no'ları ve test cevapları depo raporundan açılan kartlara taşındı. 35 stok kartı kaldı.
  - Stoktan siparişe atarken "Tekrar test edilecek" hazır seçili geliyor (Teste hazır'dan devam); "Test gerekmiyor" seçilirse Temizlik'ten devam.
  - "Bekleyen sipariş" sütunu "Atanabilir sipariş" oldu, yanında "atanmadı" yazıyor. Sipariş ürününde "Bu ürün stoktan karşılanmayacak" düğmesi var.
  - Stok ekranında yeni bölüm: stok için montajı devam eden iş emirleri.
  - "Stok makinesi ekle" sağ üstte açılır kutu oldu.
- Siparişler panosu ekranın bütün genişliğini kullanıyor; menü genişleyince pano kayıyor ve daralıyor.
- Karanlık tema:
  - Sağ üstte (telefonda üst çubukta) kullanıcının gönderdiği görseldeki gibi bir düğme var. Seçim tarayıcıda hatırlanıyor; seçim yoksa bilgisayarın ayarı izleniyor.
  - Stil dosyasındaki renkler renk adlarına çevrildi; karanlıkta yalnızca bu adların değeri değişiyor.
  - Özetteki planlama pastasının renk sırası karanlıkta tersine dönüyor.
- MONTAJ yazısı logonun genişliğiyle büyüyor (logonun yaklaşık %96'sı), logodan taşmıyor ve biraz daha aşağıda.
- 146 otomatik test geçiyor; gerçek verinin kopyasında 1.085 sayfa hatasız açılıyor; karanlık ve aydınlık ekranlar görüntüyle kontrol edildi.

## Sıradaki iş

1. Kullanıcının denemesi: açık bütün `baslat.bat` pencereleri kapatılıp yeniden açılır (göç 19 çalışır). Tema düğmesi, MONTAJ yazısı, stoktan atamada test seçimi, "stoktan karşılanmayacak" düğmesi (farklı kabin isteyen sipariş için) ve Stok ekranındaki yeni bölüm denenir.
2. 4. adımın kalan parçaları, her biri önce sorularla: kontrol listesi ve PP şablonu, fotoğraf, kart kart atama ve etiketler.
3. Stok test sorusunun Yapılacaklar'a eklenmesi (isteğe bağlı) ve Yapılacaklar'ın sadeleştirilmesi: kullanıcıya hâlâ karışık geliyor.
4. Stok için montajı devam eden makinelerin panoda da görünmesi (isteğe bağlı; kullanıcı yalnızca Stok ekranını istedi).
5. SVR ve OVR formları (test formu ve montaj öncesi kalite kontrol formları): kullanıcı hazır olunca.
6. ERP'den canlı veri (API, 15 dakikada bir): ERP sorumlusundan adres, belge ve salt okunur erişim gelince.

## Kullanıcıdan beklenenler

- Yeni ekranları denemek; farklı kabin isteyen siparişin ürününü "stoktan karşılanmayacak" diye işaretlemek.
- PP-796-VM hiçbir ERP listesinde görünmüyor: ERP'de stok girişinin neden olmadığını depoya ya da planlamaya sormak.
- Proje takip kartının son hâlini onaylamak (örnekler `OMS Veri/taslaklar/`).
- PP-908'in test öncesi kontrol formunu ve 9XX test formunu hazırlanınca `OMS Veri/uygulama/formlar/` klasörüne koymak; o zamana kadar PP-908'de çıktı alınamaz.
- ERP'deki hatalı ve boş yarı mamul rotalarını güncellemek.
- "Makine numaraları" şablonunu doldurup yüklemek (şasi no'lar; iki motorlu PP'lerde ikinci motor).
- Asistan: Anthropic'in iade cevabı gelince denemeye karar vermek.
- ERP sorumlusundan: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
