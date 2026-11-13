# Kaldığımız yer

**13/11/2026, 17:28.** Kontrol listesi ve PP şablonu yazıldı (4. adımın 2. parçası); liste tamamlanmadan ürün Sevke hazır'a geçmiyor. Kullanıcının denemesini bekliyor.

## Bu oturumda yapılanlar

- Ürün sayfasında "Kontrol listesi" bölümü (göç 24):
  - Güç ünitesinde çalışma sırasıyla: pompa montajı, opsiyonel ekipmanların montajı, motor açılışı, motor eksperi, metal etiket. SVR ve OVR'de yalnızca metal etiket. Bakım-onarım kartında liste yok.
  - Stoktaki makinede de var; makine siparişe atanınca işaretler siparişin ürününe geçiyor.
  - Motor açılışı işaretlenirken yapıldığı gün soruluyor (bugünden ileri olamaz).
  - Pompa montajı: iş emrinde pompa montajı kırılımı stoğa girince kendiliğinden tamamlanıyor; kırılımı yoksa ekip işaretliyor.
  - Opsiyonel ekipman maddesi ayrıca işaretlenmiyor; ekipmanın montaj durumu "Montaj tamamlandı" olunca tamamlanıyor.
  - Motor eksperi: Yapılacak (kartta ve panoda "Eksper bekleniyor") · Yapılmayacak · Yapıldı (günüyle). Sevk kuralına girmiyor.
  - Siparişteki güç ünitesinde "müşterinin kabin seri no'su" yazılıyor.
- Kural: kontrol listesi tamamlanmadan ürün Sevke hazır'a ve Sevk edildi'ye geçmiyor; eksikler ürün sayfasının aşama kutusunda yazıyor. Kural başladığında Sevke hazır ya da Sevk edildi aşamasındaki ürünler muaf.
- Panodaki kartta "Kontrol x/y" satırı. Her işaret ve geri alma zaman akışına yazılıyor.
- 160 otomatik test geçiyor. Gerçek verinin kopyasında göç çalıştı, 543 sayfa hatasız açıldı; test ya da temizlikte bekleyip kurala hemen takılan makine yok. Açık güç ünitelerinin yalnızca birkaçında pompa kırılımı bulunuyor; gerisinde ekip işaretleyecek.

## Sıradaki iş

1. Kullanıcının denemesi: açık bütün `baslat.bat` pencereleri kapatılıp yeniden açılır (göç 24 çalışır). Bir güç ünitesinde kontrol listesi doldurulur, Sevke hazır'a geçiş denenir. Kullanıcı ardından ERP Excel'lerini güncelleyip yükleyecek; sonuçlara birlikte bakılır.
2. 4. adımın kalan parçaları, her biri önce sorularla: fotoğraf; kart kart atama ve etiketler ("Volvo açılış için bekleniyor" etiketi dahil).
3. ERP'den canlı veri (API, 15 dakikada bir): kullanıcı ERP uzmanıyla görüşecek; istenecekler listesi hazırlanabilir.
4. Yapılacaklar'ın sadeleştirilmesi (kullanıcıya hâlâ karışık geliyor); stok test sorusunun oraya eklenmesi isteğe bağlı.
5. Siparişi iptal edilip stoğa alınan makinenin bilgileriyle stok kartına dönüşmesi: ERP'de iptalin nasıl göründüğü bir örnekle netleşince.
6. SVR ve OVR formları (test formu ve montaj öncesi kalite kontrol formları; bakım-onarımları da): kullanıcı hazır olunca.

## Kullanıcıdan beklenenler

- Kontrol listesini denemek; eksik ya da fazla madde varsa söylemek.
- Güncel ERP Excel'lerini yüklemek.
- ERP uzmanından: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Siparişi ERP'de iptal edilmiş bir makinenin örneği (iptalin listelerde nasıl göründüğü).
- PP-796-VM hiçbir ERP listesinde görünmüyor: ERP'de stok girişinin neden olmadığını depoya ya da planlamaya sormak.
- PP-908'in test öncesi kontrol formunu ve 9XX test formunu hazırlanınca `OMS Veri/uygulama/formlar/` klasörüne koymak.
- ERP'deki hatalı ve boş yarı mamul rotalarını güncellemek.
- "Makine numaraları" şablonunu doldurup yüklemek (şasi no'lar; iki motorlu PP'lerde ikinci motor).
- Asistan: Anthropic'in iade cevabı gelince denemeye karar vermek.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
