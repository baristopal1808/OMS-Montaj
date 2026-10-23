# Kaldığımız yer

**23/10/2026, 17:10.** 3. adım (iş emirleri) yazıldı ve kullanıcının denemesini bekliyor: bağlanamayan iş emirleri, eksik malzeme ve "İmalatta" uyarısı Yapılacaklar'da soruluyor. Sırada kullanıcının denemesi ve 4. adım var.

## Bu oturumda yapılanlar

- Yapılacaklar ekranı (`yapilacaklar.py`). Üç konu var:
  - **Eksik malzeme** (`uyarilar.py`): "Çıkış yapılamayan malzeme" raporu yükleniyor. Ürün sayfasında eksikler kırılım kırılım görünüyor; depoda olan sarı, olmayan kırmızı. İş emri başına "Bilginiz var mı?" diye soruluyor. Yeni eksik gelirse soru yeniden geliyor.
  - **ERP'de "İmalatta":** iş emri stoğa girmiş ama ERP "İmalatta" diyor. Her ürün ve iş emri için ayrı soruluyor.
  - **Bağlanamayan iş emirleri:** hangi siparişe ait olduğunu ekip seçiyor.
- Yapılacaklar'ın görünümü:
  - Konu ve ürün ailesi süzgeçleri var. Aile seçilince bölümler çıkıyor (PP'de motor-pompa hattı, hortum seti…).
  - Kaydet sayfayı yenilemiyor, liste yerinde kalıyor.
- İki motorlu güç üniteleri (model no 1000 ve üstü): "Motor 1 seri no" ve "Motor 2 seri no" ayrı ayrı görünüyor.
  - Göç 11 ile ikinci motor alanı eklendi.
  - Motor no ERP'den okunurken önce iş emrinin kendi açıklamasına bakılıyor.
- Siparişler ekranındaki kutucuklarda tam ürün kodu yazıyor.
- Birlikte yüklenen ERP listeleri doğru sırayla işleniyor: siparişler, iş emirleri, eksik malzeme.
- Yapay zekâ asistanı:
  - Her ekranın sağ altında sohbet kutusu; `baslat.bat` gerçek veriyle açıyor.
  - Kullanıcının OMS simgesi 128×128 boyutunda sayfaya gömülü; üzerine gelince "Montaj Asistanı" yazısı kayarak çıkıyor.
  - Kutu açılırken büyüyerek açılıyor.
  - Kullanıcı Anthropic'in iade cevabını beklediği için şimdilik soru sormuyor.
- Göçler 9–12. 117 otomatik test geçiyor; gerçek verinin kopyasında 885 sayfa hatasız açılıyor.

## Sıradaki iş

1. Kullanıcının 3. adımı denemesi: eksik malzeme raporunu yeniden yükleyip Yapılacaklar'daki soruları cevaplaması. Gelen düzeltmeler yapılır.
2. 4. adım (ürün sayfası ve pano): aşama değiştirme, kontrol listeleri ve PP şablonu, notlar ve zaman akışı, fotoğraf, atama, etiketler, pano. Eksik satır uyarısına "Kontrol ettim, satır silinmiş" düğmesi. Önce sorular adım adım sorulur.
3. Yapılacaklar'daki soru sayısı (bugün 93) fazla gelirse azaltma: örneğin eksik malzeme yalnızca teslimi yakın siparişlerde sorulur.
4. ERP'den canlı veri (API, 15 dakikada bir): ERP sorumlusundan adres, belge ve salt okunur erişim gelince.

## Kullanıcıdan beklenenler

- `baslat.bat`'ı yeniden açıp "Çıkış yapılamayan malzeme" raporunu bir kez daha yüklemek (önceki yükleme yalnızca tanınmıştı, kaydedilmemişti).
- Yapılacaklar'daki soruları deneyip görüşlerini söylemek.
- "Makine numaraları" şablonunu doldurup yüklemek (şasi no'lar; iki motorlu PP'lerde ikinci motor).
- Asistan: Anthropic'in iade cevabı gelince denemeye karar vermek.
- ERP sorumlusundan: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
