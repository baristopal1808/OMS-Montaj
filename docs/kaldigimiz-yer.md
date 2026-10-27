# Kaldığımız yer

**27/10/2026, 18:04.** 3. adımın kullanıcıdan gelen düzeltmeleri yapıldı (eksik malzemenin görünümü, imalattan beklenen yarı mamuller, kilitli makine numaraları, opsiyonel ekipmanlar); kullanıcının denemesini bekliyor. Sırada deneme ve 4. adım var.

## Bu oturumda yapılanlar

- Eksik malzeme:
  - Ürün sayfasında kırılımlar tıklanır liste; tıklanan kırılımın eksikleri altında açılıyor. Kırılım tablosundaki eksik sayısı da ilgili kırılımı açıyor.
  - İmalat fabrikasından gelen yarı mamuller ayrı bölümde ("İmalattan beklenen yarı mamuller"). Parça parça ya da "Hepsi geldi" ile işaretleniyor, geri alınabiliyor; işaret rapor yeniden yüklense de kalıyor (göç 13).
  - "Bilginiz var mı?" sorusu yalnızca satın alınan malzemeler için. Gerçek veride eksik malzeme soruları 52'den 38'e indi.
- İş emri sayfası (`/is-emri/<no>`): ürüne dağıtılmayan iş emirleri (alt montaj, yarı mamul) için; sipariş kartındaki iş emri numarası buraya gidiyor.
- Makine numaraları kilitli:
  - Motor seri no (iki motorlularda iki numara) ve şasi no ürün sayfasının başında, sipariş ve müşterinin yanında.
  - Numara bir kez girilince kilitleniyor. Değiştirmek için "Değiştir", uyarı ve zorunlu sebep; değişiklik geçmişi saklanıyor (göç 13).
  - "Makine numaraları" şablonu yalnızca boş numaraları dolduruyor.
- "PP'ye takılacak" yerine "Opsiyonel ekipmanlar"; son durum "Montaj tamamlandı" ve sipariş kartında görünüyor.
- Sipariş kartında her ürünün satırında seri no, iş emri ve motor/şasi no aynı satırda; kirişte "Seri no yok" yerine iş emri numarası.
- 119 otomatik test geçiyor; gerçek verinin kopyasında 1.256 sayfa hatasız açılıyor. Yapılacaklar'da bugün 76 soru (38 eksik malzeme, 5 İmalatta, 33 bağlanamayan).

## Sıradaki iş

1. Kullanıcının denemesi: `baslat.bat` yeniden açılınca göç 13 çalışır. Ürün sayfasındaki kırılımlar, yarı mamullerde "Geldi", numaraların kilidi ve Yapılacaklar'daki sorular denenir; gelen düzeltmeler yapılır.
2. 4. adım (ürün sayfası ve pano): aşama değiştirme, kontrol listeleri ve PP şablonu, notlar ve zaman akışı, fotoğraf, atama, etiketler, pano. Eksik satır uyarısına "Kontrol ettim, satır silinmiş" düğmesi. Önce sorular adım adım sorulur.
3. Yapılacaklar'daki soru sayısı fazla gelirse azaltma: örneğin eksik malzeme yalnızca teslimi yakın siparişlerde sorulur.
4. ERP'den canlı veri (API, 15 dakikada bir): ERP sorumlusundan adres, belge ve salt okunur erişim gelince.

## Kullanıcıdan beklenenler

- Yeni ekranları deneyip görüşlerini söylemek.
- Yarı mamuller için kalıcı çözüm: imalat fabrikasının parçayı gönderirken ERP'de depo transferi, montajın da iş emrine çıkış yapması. ERP sorumlusu ve planlamayla konuşulacak.
- "Makine numaraları" şablonunu doldurup yüklemek (şasi no'lar; iki motorlu PP'lerde ikinci motor).
- Asistan: Anthropic'in iade cevabı gelince denemeye karar vermek.
- ERP sorumlusundan: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
