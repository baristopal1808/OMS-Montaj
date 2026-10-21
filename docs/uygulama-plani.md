# Uygulama planı

**Kullanıcı onayladı, 21/10/2026.** Bağımlılıklar (5. bölüm) ve WhatsApp bildiriminde (a) seçeneği de onaylandı. Kararların ayrıntısı ve gerekçeleri `docs/ihtiyaclar.md` dosyasında.

## 1. Kısaca

Montaj ekibinin takibi (sipariş → malzeme hazırlık → montaj → test → sevk) Planner'dan kendi uygulamamıza taşınır. Uygulama şirket sunucusunda çalışan bir web sitesidir; şirket ağındayken bilgisayardan ve telefondan açılır. Verisini ERP'den alınan Excel listelerinden okur, ERP'ye hiçbir şey yazmaz. Aşamaları, kontrol listelerini, seri numaralarını, notları ve fotoğrafları ekip uygulamada tutar.

## 2. İlk sürümde neler olacak

### Ekranlar

| Ekran | Ne yapar |
|---|---|
| Giriş | Herkes kendi kullanıcı adı ve şifresiyle girer. |
| Siparişler (ana ekran) | Açık siparişler teslim tarihine göre sıralanır: yaklaşan turuncu, geçen kırmızı, onay bekleyen soluk görünür. Süzgeçler: ürün ailesi ve model (hazır "Vibrohammer" süzgeci dahil), etiket, sipariş tipi, bana atananlar. Arama: sipariş no, İEN, seri no, müşteri. |
| Sipariş kartı | Siparişin başlığı: sipariş no, müşteri, tip, teslim ve onay tarihi, sipariş notu. Ürünler bölüm bölüm (vibrohammer, PP, çene, kiriş…); her birinin aşaması, bağlı kartları ve uyarıları. Aksesuarlar ve projeye özel ürünler listesi. "Depoda stok mevcut" bilgisi ve atama. |
| Ürün sayfası | Aşama; kontrol listesi; bilgi alanları (seri no, çene no, motor seri no, renk, yağ…); bağlı kartlar; ERP bilgileri (iş emri, planlama biriminin ürün üretim durumu ve verinin tarihi, eksik malzeme özeti); atanan kişiler; etiketler; fotoğraflar; zaman akışı. |
| Pano | Aşama sütunları; her ürün kendi aşamasının sütununda. Bilgisayarda kart sürüklenerek, telefonda "Aşamayı değiştir" düğmesiyle taşınır. |
| Stok | Siparişe bağlanmamış ürünler: depo, test durumu, seri ve çene no. Siparişe buradan atanır. |
| Yapılacaklar | Uygulamanın sorduğu her şey tek listede: bağlanamayan iş emri hangi siparişe, testi yapıldı mı, sevk edildi kartı kapatayım mı, yağ bilgisi yok, Planner'da eşleşmeyen kart, gelen hata bildirimleri. |
| ERP yükleme | Excel listeleri yüklenir; uygulama neyin değiştiğini özetler (yeni sipariş, yeni iş emri, tamamlanan, sevk edilen). Son yüklemenin tarihi görünür. |
| Ayarlar | Etiketler, aşamalar, kontrol listesi şablonları, hangi ürün kodunun kart olacağı, varsayılan atama, kullanıcılar. |
| Planner arşivi | Tamamlanmış Planner kartları; değiştirilemez, İEN, seri no ya da sipariş no ile aranır. |

### Kurallar (özet)

- Her fiziksel ürünün bir kartı olur. Kartlar ERP'nin sipariş ve iş emri listelerinden oluşur.
- Aşamalar `ihtiyaclar.md` 3.1'deki listeyle başlar. ERP kartı yalnızca "Sipariş" ve "Malzeme hazırlık" aşamalarına getirir; gerisini ekip ilerletir.
- ERP verisi ekibin elle girdiği bilgiyi ezmez; çelişki varsa uygulama sorar.
- Bağlantısı ERP'de görünmeyen ürünler kullanıcıya sorularak bağlanır.
- Kontrol listeleri ürün ailesinin şablonundan gelir. Kablosuz kumanda, uzaktan erişim gibi maddeler yalnızca siparişte varsa gelir.
- Zaman akışında kimin ne zaman ne yaptığı görünür: notlar, aşama değişiklikleri, ERP olayları, hata bildirimleri.
- İki rol var: Ekip her şeyi yapar. İzleyici (genel müdür, fabrika müdürü) bakar ve hata bildirir, değiştiremez.

### Kurulumda bir kez yapılacaklar

- Eldeki stokların kaydı: stok raporundan çıkan her adede çene ya da seri no girilir.
- Planner Excel'i: açık kartların notlarındaki numaralar ERP'de eşleşen kartlara doldurulur; tamamlanmış kartlar arşive alınır.
- Kullanıcının gönderdiği önemli Planner sohbet notları ilgili kartlara eklenir.
- Kullanıcılar, varsayılan atamalar ve PP şablonu girilir.

## 3. Sonraki sürümlere kalanlar

- Takvim ve grafik görünümleri
- E-posta bildirimleri (denemelerden sonra karar verilecek)
- Vibrohammer ve diğer ailelerin kontrol listesi şablonları (Ayarlar'dan ilk sürümde de eklenebilir)
- Servis takibinin ayrıntısı (denemelerde birlikte çalışılacak)
- Uygunsuzluk ve DÖF uyarısı
- ERP'ye doğrudan bağlantı (Excel yüklemesinin yerine)
- Yetkilerin kişi kişi ayarlanması

## 4. Nasıl kurulacak

- **Web uygulaması.** Sunucuda sürekli çalışan bir program; tarayıcıdan açılır. Sayfalar sunucuda hazırlanıp telefona hazır gelir, bu yüzden telefonda da hızlı açılır.
- **Dil ve veritabanı.** Python 3.12. Veriler SQLite'ta durur; SQLite tek bir dosyadan oluşan bir veritabanıdır. Eski portalla aynı aileden, ama kodu ve veritabanı tamamen ayrı.
- **Parçalar:**
  - *ERP okuyucu:* Excel listelerini okuyup uygulamanın anladığı biçime çevirir. Doğrudan ERP bağlantısı gelince yalnızca bu parça değişir.
  - *Eşleştirici:* Her yüklemede ERP'yi uygulamadaki kayıtlarla karşılaştırır. Olayları üretir ("iş emri açıldı", "ERP'de tamamlandı", "sevk edildi"), sorulacakları Yapılacaklar'a yazar.
  - *Uyarı kaynakları:* Bugün eksik malzeme uyarısı; uygunsuzluk ve DÖF ileride aynı yere eklenir.
  - *Ekranlar.*
- **Sunucuda.** Eski portal gibi Docker ile, aynı sunucuda ayrı bir adreste çalışır. Docker, programı ihtiyaç duyduğu her şeyle birlikte kendi kutusunda çalıştıran bir araçtır. Veritabanı, fotoğraflar ve yüklenen Excel'ler kutunun dışında, sunucudaki bir klasörde durur; böylece güncellemede kaybolmaz ve yedeklenebilir.
- **Geliştirme sırasında** uygulama kullanıcının bilgisayarında çalışır; gerçek veri `OMS Veri/uygulama/` klasöründe durur.

## 5. Eklenecek bağımlılıklar (onay gerekiyor)

Bağımlılık, uygulamanın kullandığı ve başkalarının yazdığı hazır bir program parçasıdır. Aşağıdakilerin hepsi yaygın, ücretsiz ve açık kaynaktır.

| Bağımlılık | Ne için |
|---|---|
| Flask | Web sayfalarını sunmak; Python'daki en yaygın küçük web çatılarından biri. Kendi küçük yardımcılarını da getirir. |
| Waitress | Uygulamayı sunucuda sürekli ve güvenli çalıştırmak; Windows'ta da çalışır |
| openpyxl | .xlsx dosyalarını okumak |
| xlrd | ERP'nin verdiği eski .xls dosyalarını okumak |
| Pillow | Telefondan çekilen büyük fotoğrafları küçültmek |
| Inter yazı tipi dosyaları | Yazı tipi; uygulamanın içine konur, internet gerekmez; lisansı serbest |
| pytest (yalnızca geliştirmede) | Otomatik testler |

Kütüphaneler projeye özel bir klasöre (sanal ortam) kurulur; bilgisayardaki diğer programları etkilemez. Docker sunucuda zaten var.

## 6. Veri güvenliği

- Gerçek veri (veritabanı, Excel'ler, fotoğraflar) git'e girmez. Geliştirmede `OMS Veri/` klasöründe, sunucuda veri klasöründe durur.
- Testler ve örnekler uydurma veriyle yazılır (CLAUDE.md, kural 3).
- Şifreler geri çevrilemez biçimde saklanır; kimse okuyamaz.
- Uygulama yalnızca şirket ağından açılır ve ERP'ye yazmaz.
- Sunucudaki veri klasörü düzenli yedeklenir; nasıl yapılacağı kurulumda IT ile belirlenir.
- WhatsApp için girilen telefon numaraları yalnızca uygulamanın veritabanında durur.

## 7. Hata bildirimi WhatsApp'a nasıl gider? (soru 42; kullanıcı (a)'yı seçti)

- **(a) WhatsApp bağlantısı.** Müdür "Atanan kişiye hata bildir"e basınca WhatsApp hazır mesajla açılır; müdür yalnızca "Gönder"e basar. Kurulum ve ücret yok; kişilerin telefon numaraları uygulamaya bir kez girilir. Karta iki kişi atanmışsa müdür hangisine göndereceğini seçer. Bilgisayarda WhatsApp Web ya da masaüstü uygulaması açılır.
- **(b) Tam otomatik gönderim (WhatsApp Business API).** Mesajı sunucu kendisi gönderir. Meta'da onaylı bir işletme hesabı ve numara, mesaj şablonlarının onayı, sunucunun internete çıkışı ve IT desteği gerekir; mesaj başına ücret olabilir.

Öneri: (a). İki yolda da bildirim kartın zaman akışına "Hata bildirimi" olarak yazılır ve atanan kişinin Yapılacaklar listesine düşer.

## 8. Geliştirme adımları

Her adımın sonunda kullanıcı deneyebileceği bir şey görür. Kullanıcı dener, düzeltmeler yapılır, `/kaydet` ile kaydedilir.

İlerleme:

- 1. adım bitti (21/10/2026). Kullanıcının isteğiyle giriş ekranı, logo ve yan menü eklendi.
- 2. adım yazıldı (21/10/2026); kullanıcının denemesini bekliyor. Gerçek listelerle denendi: 131 sipariş, 419 kalem, 331 ürün kartı.

| Adım | Ne yapılır | Kullanıcı ne dener |
|---|---|---|
| 1. İskelet | Proje yapısı, giriş, kullanıcılar ve roller, Inter yazı tipi, boş ekranlar | Bilgisayarda ve telefonda açıp giriş yapar |
| 2. Siparişler | Sipariş talepleri listelerinin yüklenmesi; siparişler listesi, sipariş kartı, ürün kartlarının oluşması (seri no, teslim tarihi, renk, yağ, aksesuarlar, onay bekleyenler) | Gerçek listeyi yükleyip siparişleri görür |
| 3. İş emirleri | Açık ve kapalı iş emirlerinin yüklenmesi; bağlantılar, alt montaj kartları, "Malzeme hazırlık" geçişi, "ERP'de tamamlandı" olayı; Yapılacaklar listesi | Kartların iş emirleriyle doğru eşleştiğine bakar |
| 4. Ürün sayfası ve pano | Aşama değiştirme, kontrol listeleri ve PP şablonu, bilgi alanları, notlar ve zaman akışı, fotoğraf, atama, etiketler, pano | Bir ürünü baştan sona ilerletir |
| 5. Stok, test ve sevk | Stok raporları, ilk stok kaydı, "depoda stok mevcut", test sorusu ve "test bekliyor" uyarısı, eksik malzeme uyarısı, "sevk edildi, kapatayım mı?" | Stokları kaydeder, bir stok ürününü siparişe atar |
| 6. Ayarlar ve izleyici | Etiket, aşama, şablon, kart kuralı, atama ve kullanıcı ekranları; izleyici rolü ve hata bildirimi | Bir etiket ekler; müdür hesabıyla hata bildirir |
| 7. Planner'dan alım | Açık kartların notlarındaki numaralar, Planner arşivi, önemli sohbet notları | Arşivde eski bir makineyi arar |
| 8. Sunucuya kurulum | Docker, adres, veri klasörü (logo dahil) ve yedek; telefon için bağlantı | Ekip şirket ağında kullanmaya başlar |

## 9. Deneme ve geçiş

- 8. adımdan sonra ekip uygulamayı Planner'la birlikte kullanır.
- Aşamalar, şablonlar, servis takibi ve e-posta bildirimleri bu sürede netleşir.
- Uygulama oturunca Planner bırakılır.
