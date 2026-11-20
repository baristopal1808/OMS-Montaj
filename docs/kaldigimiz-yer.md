# Kaldığımız yer

**20/11/2026, 19:32.** Kullanıcının 19/11 istekleri yazıldı ve kaydedildi (süzgeç, Özet, motor açılışı ve WhatsApp mesajı, sade ürün sayfası, asistan). Kullanıcı son özeti henüz okumadı; denemesini bekliyor.

## Oturum açılınca ilk iş

Kullanıcı bu oturumun son özetini okumadan kapattı ve bir sonraki sefer olduğu gibi anlatılmasını istedi. Yeni oturumun ilk mesajında aşağıdaki "Kullanıcıya anlatılacaklar" bölümünü kısaltmadan anlat, sonra sıradaki adımı sor. Anlattıktan sonra bu bölüm bir sonraki `/kaydet`te silinir.

## Kullanıcıya anlatılacaklar

İstediğiniz değişikliklerin hepsini yaptım. Otomatik testlerin hepsi geçiyor (165). Gerçek verinin bir kopyasında 962 sayfa hatasız açıldı. Ekranları tarayıcıda kendim göremedim; görünüşte tuhaf bir şey görürseniz söyleyin.

**Kayıt işi:** Ayarlara GitHub'a gönderme izni ekledim; kayıtlar artık takılmadan gönderiliyor. Zorla gönderme bu iznin dışında kaldı.

**Yapılanlar**

- **Siparişler süzgeci:** PP'ye süzüp başka ekrana geçince süzgeç artık yerinde kalıyor. Kaldırmak için "Süzgeçleri temizle" düğmesi var. Özet'teki bağlantılar (teslimi geçen gibi) kendi süzgeciyle açılıyor, sizinkini bozmuyor.
- **Özet:** Ekran sağa doğru genişledi. Tablo ikiye ayrıldı: solda makine, sağda yedek parça siparişleri.
- **Pompa montajı** sorusu kaldırıldı.
- **Motor açılışı:**
  - Kabin testi bitene kadar "kabin testi tamamlanınca sorulur" yazıyor, işaretlenemiyor.
  - Kabin Test'ten Temizlik'e geçince bir pencere açılıyor ve hazır mesajı gösteriyor. "WhatsApp'ta mesajı aç"a basınca mesaj yazılmış olarak açılıyor, siz yalnızca Gönder'e basıyorsunuz.
  - Mesaj yalnızca Volvo motorlu kabinlerde öneriliyor; CAT motorlularda yalnızca "yapıldı mı?" sorusu geliyor.
  - Düğmeye basılınca zaman akışına "haber verildi" yazılıyor. Mesajın gerçekten gönderilip gönderilmediğini uygulama bilemiyor.
- **Ürün sayfası:**
  - Aşama kutusunda yalnızca bulunulan aşama yazıyor. Üzerine gelince (telefonda dokununca) baloncukta bütün sıra çıkıyor: geçilenler yeşil, bulunulan kırmızı, önündekiler soluk. Aşama değiştirme yerinde duruyor.
  - Notlar ve zaman akışı kırmızı başlıktaki düğmeyle açılan pencerede.
  - Bilgisayarda sayfa iki sütun oldu, yazılar yaklaşık %12 küçüldü. Telefonda tek sütun ve yazılar eski boyutta.
- **Müşterinin kabin seri no'su** artık yalnızca o müşterinin güç ünitelerinde soruluyor. Müşteri kodu git'e girmesin diye bunu `OMS Veri` içindeki müşteri dosyasına yazdım (o müşterinin satırına "kabin_seri=evet" ekledim).
- **Asistan:** Önce aşamayı ve teslime kalan süreyi söyleyecek, sonra yalnızca sorunlu noktaları; en çok 4 kısa satır ve ERP terimi yok. Ayrıntıyı ancak siz isterseniz verecek. Gerçek bir soruyla denemedim; denedikten sonra gerekirse yeniden ayarlarız.

**Sizin yapmanız gereken:** Mesajın gideceği kişinin hitabını ("… Bey") ve telefonunu **Ayarlar > Motor açılışı** ekranından girin. Kişi bilgisi git'e girmesin diye bunlar koda yazılmadı.

**Denemek için:** Önce `baslat.bat` pencerelerini kapatıp yeniden açın; veritabanı değişikliği (göç 25) böyle çalışır. Sonra:

1. Ayarlar'dan hitap ve telefonu girin.
2. Test aşamasındaki bir kabini Temizlik'e alın; pencere açılmalı.
3. Ürün sayfasının yeni düzenine bakın.
4. Siparişler'de PP'ye süzün, Özet'e gidip geri dönün; süzgeç yerinde olmalı.

**Sıradaki adımlar (önerdiğim sıra)**

1. Kart kart atama ve etiketler ("Volvo açılış için bekleniyor" dahil).
2. Fotoğraf ekleme.
3. "Sevk edildi, kapatayım mı?" sorusu ve yedek parçanın aşamaları (Hazırlanıyor, Sevke hazır).
4. **Sunucuya kurulumu (8. adım) öne almanızı öneririm.** Böylece ekip uygulamayı Planner'la birlikte hemen kullanmaya başlar. Ayarlar ekranları (6. adım) ve Planner arşivi (7. adım) kullanım sırasında eklenebilir.

Bunlarla birlikte yürüyecek işler: ERP'den canlı veri (API bilgileri ERP uzmanından gelince), SVR ve OVR formları.

## Bu oturumda yapılanlar

- GitHub'a gönderme izni `.claude/settings.json` dosyasına eklendi (yalnızca `git push` ve `git push -u origin main`).
- Siparişler süzgeci tarayıcı oturumunda saklanıyor; "Süzgeçleri temizle" düğmesi.
- Özet tam genişlikte; teslim tablosu makine ve yedek parça olarak ikiye ayrıldı.
- Kontrol listesinden pompa montajı kalktı. Motor açılışı kabin testi bitince (Temizlik ve sonrası; stokta test edildiyse) işaretlenebiliyor.
- Motor açılışı penceresi ve hazır WhatsApp mesajı (`oms_montaj/motor_acilisi.py`, göç 25: `ayarlar` tablosu). Ayarlar > Motor açılışı ekranında hitap, telefon ve mesaj metni. Yalnızca Volvo motorlu kabinde mesaj önerilir.
- Ürün sayfası: tek aşama etiketi ve sıra baloncuğu, notlar ve zaman akışı pencerede, geniş ekranda iki sütun, bilgisayarda küçük yazılar.
- Kabin seri no'su sorusu yalnızca `marka/musteriler.txt` içinde `kabin_seri=evet` yazan müşteride.
- Asistanın yönergesi kısa ve sade cevaba göre yeniden yazıldı.
- 165 otomatik test geçiyor. Gerçek verinin kopyasında göç 25 çalıştı, 962 sayfa hatasız açıldı.

## Sıradaki iş

1. Kullanıcıya yukarıdaki "Kullanıcıya anlatılacaklar" bölümünü anlatmak; sonra denemesi (baslat.bat yeniden açılır, Ayarlar > Motor açılışı doldurulur, bir kabin Test'ten Temizlik'e alınır).
2. 4. adımın kalan parçaları, her biri önce sorularla: kart kart atama ve etiketler ("Volvo açılış için bekleniyor" dahil); fotoğraf.
3. "Sevk edildi, kapatayım mı?" sorusu ve yedek parça aşamaları.
4. Sunucuya kurulumun öne alınması (kullanıcının kararı bekleniyor).
5. ERP'den canlı veri (API, 15 dakikada bir): kullanıcı ERP uzmanıyla görüşecek.
6. Yapılacaklar'ın sadeleştirilmesi; siparişi iptal edilip stoğa alınan makine; SVR ve OVR formları.

## Kullanıcıdan beklenenler

- Son değişiklikleri denemek; Ayarlar > Motor açılışı'na hitap ve telefonu girmek.
- Asistana gerçek bir soru sorup cevabın kısalığına bakmak.
- Sunucuya kurulumun öne alınıp alınmayacağına karar vermek.
- Güncel ERP Excel'lerini yüklemek.
- ERP uzmanından: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Siparişi ERP'de iptal edilmiş bir makinenin örneği.
- PP-796-VM'nin ERP'de neden görünmediğini depoya ya da planlamaya sormak.
- PP-908'in test öncesi kontrol formunu ve 9XX test formunu `OMS Veri/uygulama/formlar/` klasörüne koymak.
- ERP'deki hatalı ve boş yarı mamul rotalarını güncellemek.
- "Makine numaraları" şablonunu doldurup yüklemek.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
