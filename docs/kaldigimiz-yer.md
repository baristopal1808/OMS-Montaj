# Kaldığımız yer

**10/11/2026, 14:43.** Proje takip kartı iki dilli oldu; stok makinesine iş emri ya da stok giriş no ve opsiyonel ekipman girilebiliyor; bakım-onarım için gelen güç ünitesinde de dört form basılıyor. Kullanıcının denemesini bekliyor.

## Bu oturumda yapılanlar

- Proje takip kartı:
  - Siparişteki opsiyonel ekipman (uzaktan erişim modülü, kablosuz kumanda seti) ayrı satırda yazıyor.
  - Yazılar ve kırmızı etiketler büyüdü.
  - Kart iki dilli: üstte İngilizce, altında küçük Türkçe. Sabit değerler de çevriliyor (Without oil / Yağsız sevk…).
  - Birden çok test vibrosu tek satıra sığmıyorsa alt alta basılıyor; sığmayan değer küçülüyor.
  - Opsiyonel ekipman adları kelimelerin ilk harfi büyük yazılıyor (bütün ekranlarda).
- Stoktaki güç ünitesinin proje takip kartı basılıyor; sipariş no'nun yerinde STOK yazıyor (göç 20). Yeniden basarken son kartın test vibrosu ve yağı hazır geliyor.
- Stok makinesine "İş emri no" ya da "Stok giriş no" yazılıyor (göç 21). ERP listelerinde olmayan iş emri yazıldığı gibi saklanıyor; ileride listede görünürse karta kendiliğinden bağlanıyor.
- Stok makinesinin opsiyonel ekipmanı kart ekranında onay kutusuyla işaretleniyor (göç 22).
- Bakım-onarım için gelen güç ünitesi:
  - Proje takip kartı, test öncesi, test ve kurulum formu basılıyor; aşama kuralı yeni makinedeki gibi. Sevk edilmiş eski bakım kartları muaf (göç 23).
  - Kartın bandı antrasit; başlığın altında "MAINTENANCE & REPAIR · Bakım-onarım" yazıyor.
  - Makinenin seri no'su ve opsiyonel ekipmanı form ekranında giriliyor.
- Ürün sayfasında aşama adları ve çıktı düğmeleri büyüdü.
- 152 otomatik test geçiyor. Gerçek verinin kopyasında sayfalar hatasız açılıyor; açık bakım siparişindeki güç ünitesinin dört formunun şablonu bulunuyor.

## Sıradaki iş

1. Kullanıcının denemesi: açık bütün `baslat.bat` pencereleri kapatılıp yeniden açılır (göç 20–23 çalışır). Denenecekler:
   - açık bakım siparişindeki güç ünitesinin formları,
   - iki dilli kart,
   - stok kabininin kartını uzaktan erişim modülü işaretli yeniden basmak,
   - stok giriş no.
2. 4. adımın kalan parçaları, her biri önce sorularla: kontrol listesi ve PP şablonu, fotoğraf, kart kart atama ve etiketler.
3. Yapılacaklar'ın sadeleştirilmesi (kullanıcıya hâlâ karışık geliyor); stok test sorusunun oraya eklenmesi isteğe bağlı.
4. Siparişi iptal edilip stoğa alınan makinenin bilgileriyle stok kartına dönüşmesi: ERP'de iptalin nasıl göründüğü bir örnekle netleşince.
5. SVR ve OVR formları (test formu ve montaj öncesi kalite kontrol formları; bakım-onarımları da): kullanıcı hazır olunca.
6. ERP'den canlı veri (API, 15 dakikada bir): ERP sorumlusundan adres, belge ve salt okunur erişim gelince.

## Kullanıcıdan beklenenler

- Yeni ekranları ve kartları denemek. İki dilli kartın ve bakım kartının örnekleri `OMS Veri/taslaklar/` klasöründe (iki-dilli-kart-…, bakim-karti-…); İngilizce terimlerde değişiklik varsa söylemek.
- Siparişi ERP'de iptal edilmiş bir makinenin örneği (iptalin listelerde nasıl göründüğü).
- PP-796-VM hiçbir ERP listesinde görünmüyor: ERP'de stok girişinin neden olmadığını depoya ya da planlamaya sormak.
- PP-908'in test öncesi kontrol formunu ve 9XX test formunu hazırlanınca `OMS Veri/uygulama/formlar/` klasörüne koymak; o zamana kadar PP-908'de çıktı alınamaz.
- ERP'deki hatalı ve boş yarı mamul rotalarını güncellemek.
- "Makine numaraları" şablonunu doldurup yüklemek (şasi no'lar; iki motorlu PP'lerde ikinci motor).
- Asistan: Anthropic'in iade cevabı gelince denemeye karar vermek.
- ERP sorumlusundan: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
