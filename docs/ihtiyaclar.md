# İhtiyaçlar ve soru-cevap

Bu belge koda başlamadan önce ihtiyaçları netleştirmek içindir: kullanıcının isteği, mevcut Planner düzeninden anlaşılanlar, yapı önerisi, açık sorular ve kararlar. Cevaplanan her soru 5. bölümdeki "Kararlar" tablosuna yazılır.

## 1. Kullanıcının isteği (19/10/2026)

İş takibi bugün Microsoft Teams Planner'da, "OMS-Montaj Fabrikası İş Planları" panosunda yapılıyor. Ürün sevk edildikçe ilgili kart tamamlanıyor. Her ürünün kartına açıklamalar yazılıyor; bunlar yeni sistemde de yer almalı. Planner Excel olarak dışa aktarılabiliyor; her alan gelmese de çoğu geliyor.

Hedefler:

1. **Ayrı uygulama.** Planner mantığını temel alan, şirketin kendi uygulaması. En uygun yapı birlikte belirlenecek.
2. **Geçmiş veri.** Planner'daki açık ve tamamlanmış kayıtlar, Excel dışa aktarımıyla uygulamaya aktarılabilmeli.
3. **ERP entegrasyonu (asıl istek).** Bilişim ERP verisiyle beslenen, ürün bazında takip. Şu durumların hepsi izlenmeli:
   - sipariş talebi geldiğinde
   - siparişe bağlı iş emri açıldığında
   - siparişten bağımsız, stok için iş emri açıldığında
   - ERP'de tamamlama yapıldığında

**ERP'ye erişim.** Şu an doğrudan bağlantı (API, veritabanı) yok; ileride olacak. O zamana kadar ERP verisi Excel ile yüklenir. Hangi raporların hangi sütunlarla alınacağını Claude söyler, kullanıcı ERP'den o şekilde çıkarır. Veri kaynağı katmanı, Excel yüklemesinin yerine doğrudan ERP bağlantısı takılabilecek şekilde kurulur; bağlantı geldiğinde uygulamanın geri kalanı değişmez.

**İleride (şimdilik kapsam dışı).** Şirket portalında uygunsuzluk ve DÖF (düzeltici-önleyici faaliyet) kayıtları tutuluyor. Bir iş emri numarasına uygunsuzluk ya da DÖF açılınca, uygulamadaki ilgili kayıtta "Uygunsuzluğu bulunmaktadır" gibi bir uyarı görünmeli. Mimari bunun sonradan eklenebileceği şekilde kurulur.

**Çalışma şekli.** Önce soru-cevapla ihtiyaçlar netleşir, sonra uygulama planı çıkar ve kullanıcı onaylar, sonra geliştirme başlar. Eski projenin dosyalarına ve reposuna dokunulmaz.

## 2. Planner'dan anlaşılanlar (kullanıcı onayı bekliyor)

Kaynak: `OMS Veri/planner/` içindeki iki ekran görüntüsü ve dışa aktarım Excel'i (2.1).

- **Pano kutulara göre gruplu; her kutu bir aşama:** Siparişler → Malzemeler hazırlık aşaması → Montajı devam edenler → Son montaj & test aşaması → Sevke hazır / Stok. Altıncı kutu: "Üretilmesi planlanan veya Üretilen Yarı Mamüller". Sevk edilen ürünün kartı tamamlanıyor; her kutunun altında "Tamamlanan görevler" sayısı görünüyor.
- **Etiketler dört tür bilgi taşıyor:** ürün grubu, kaynak (sipariş / stok), durum ve iş türü. Tam liste 2.1'de.
- **Kart başlığı:** Siparişler kutusunda "sipariş no (ürün modelleri)"; iş emri açıldıktan sonra "ürün modeli + İEN (iş emri no)".
- **Kontrol listesi iki ayrı şeyi bir arada tutuyor:**
  - bilgi: proje (sipariş) kodu, PP seri no ve müşterinin kabin için verdiği seri no, motor seri no'ları, kabin rengi (RAL), yağlı sevk (yağ türüyle) ya da yağsız sevk; bakım kartında "geldiğindeki sipariş no"
  - "yapıldı mı?" soruları: motor açılışı tamamlandı mı, metal etiket yapıştırıldı mı, uzaktan erişim modülü bağlandı mı, kablosuz kumanda seti bağlandı mı
- **Kart ayrıntısı:** durum (başlatılmadı / devam ediyor / tamamlandı), öncelik, başlangıç tarihi, son tarih (geçmişse kırmızı), yineleme, kutu, atanan kişiler, ekler.
- **Görev sohbeti:** tarihli ve kişili ilerleme notları. Örnek konular: kabinin boyadan teslim alınıp montaja başlanması, montajda fark edilen sorunlar ve bekleyen parçalar, çalıştırma ve test aşamasına geçiş. Bu notlar yeni sistemde de yer almalı.
- **Planner görünümleri:** Kılavuz (liste), Pano, Zaman çizelgesi, Takvim, Grafikler.

### 2.1 Planner Excel dışa aktarımı (19/10/2026 incelemesi)

Dosya: `OMS Veri/planner/OMS İCİN VERİ.xlsx`. Bu bölümde yalnızca yapı ve sayılar var; gerçek değerler yazılmaz.

**Sayfalar**

| Sayfa | İçerik |
|---|---|
| Plan | Plan adı, plan kimliği, dışa aktarma tarihi |
| Birleştirilmiş Veriler | Görevler; kutu ve kişi adları açık yazılı. Aktarımda bu sayfa kullanılır |
| Görevler | Aynı görevler; kutu ve kişiler kimlik numarasıyla |
| Kutular | 6 kutu (kimlik ve ad) |
| Kullanıcılar | Plandaki 5 kişi (ad ve e-posta) |
| Hedefler | Boş |

**Görevler.** 638 görev var; ilki Şubat 2025'te, sonuncusu Ekim 2026'da açılmış (2025'te 255, 2026'da 383). Durumları: 500 tamamlandı, 134 başlatılmadı, 4 devam ediyor. Tarihler metin olarak `YYYY-AA-GG` biçiminde.

**Gelen alanlar**

| Sütun | Dolu | Not |
|---|---|---|
| Görev Kimliği | 638 | Planner'ın değişmez kimliği; aynı dosya yeniden aktarılırsa eşleştirme anahtarı olur |
| Görev Adı | 638 | 447'sinde İEN geçiyor; 155'i sipariş koduyla (OZ-…) başlıyor |
| Kutu | 638 | 6 kutu (aşağıda) |
| Durum | 638 | Başlatılmadı / Devam ediyor / Tamamlandı |
| Öncelik | 638 | 635'i "Orta"; pratikte kullanılmıyor |
| Atanan | 609 | Birden çok kişi `;` ile ayrılmış; çoğunlukla 2 kişi |
| Oluşturan, Oluşturma Tarihi | 638 | |
| Son tarih | 104 | Çoğu kartta boş |
| Başlangıç tarihi | 32 | Çoğu kartta boş |
| Geciken | 638 | true / false |
| Tamamlanma Tarihi, Tamamlayan | 500 | Yalnızca gün; saat yok |
| Tamamlanan Denetim Listesi Öğeleri | 363 | Yalnızca "x/y" sayısı |
| Denetim Listesi Öğeleri | 363 | Bütün maddeler `;` ile tek hücrede |
| Etiketler | 637 | Etiket adları `;` ile ayrılmış |
| Notlar | 447 | Görev ayrıntısındaki not alanı (aşağıda) |
| Hedef, Yinelenen | 0 | Boş |

**Gelmeyenler**

- **Görev sohbeti:** dışa aktarımda hiç yok. Kartlara yazılan tarihli ilerleme notları bu yolla aktarılamaz (soru 14).
- **Ekler:** dosya ve fotoğraflar gelmiyor.
- **Kontrol listesinde hangi maddenin işaretli olduğu:** yalnızca "x/y" sayısı geliyor. 213 kartta maddelerin hepsi, 87 kartta hiçbiri, 63 kartta bir kısmı işaretli. Bu 63 kartta hangi maddenin yapıldığı bilinmiyor.
- **Kartın geçmişi:** yalnızca bugünkü kutu geliyor; kartın hangi kutuya ne zaman taşındığı gelmiyor.
- Etiket renkleri ve kutu içindeki kart sırası.

**Kutular ve durumlar**

| Kutu | Başlatılmadı | Devam ediyor | Tamamlandı |
|---|---|---|---|
| Siparişler | 21 | 0 | 130 |
| Malzemeler Hazırlık Aşaması | 50 | 0 | 19 |
| Montajı Devam Edenler | 14 | 0 | 42 |
| Son Montaj & Test Aşaması | 13 | 0 | 60 |
| Sevke Hazır / Stok | 36 | 4 | 243 |
| Üretilmesi planlanan veya Üretilen Yarı Mamüller | 0 | 0 | 6 |

Kartlar son kutuya taşınmadan, bulundukları kutuda tamamlanıyor (örneğin Siparişler'de 130 tamamlanmış kart var). "Devam ediyor" durumu neredeyse hiç kullanılmıyor; aşamayı kutu gösteriyor. STOK etiketli açık kartlar da sipariş kartlarıyla aynı kutulardan geçiyor (Malzemeler hazırlık 17, Montaj 5, Son montaj 4, Sevke hazır 17).

**Etiketler**

| Tür | Etiket (kart sayısı) |
|---|---|
| Ürün grubu | 01. PP (162), 02. SVR-NF (110), 02. SVR-VM (21), 03. OVR-S (100), 03. OVR-SG (16), 03. OVR-VM (7), 04. OVF (14), 05. WD (13), 06. SCN (176), 06. KCN (134) |
| Kaynak | SİPARİŞ (420), STOK (127), SICAK SIPARİŞ (18), YEDEK PARCA (14) |
| Durum | SEVKE HAZIR (44), Test Aşamasında (4), Volvo Bekleniyor (1) |
| İş türü | Motor Pompa Hattı (18), Yarı Mamül (13), Bakım & Onarım (6), SG CENE (2), PP Pompa Montajı (1) |
| Anlamı bilinmeyen | .V (299), DKM (27), BGM (4) |

"03.  OVR-SG" etiketi iki boşlukla yazılmış; aktarımda boşluklar sadeleştirilir.

**Görev adı.** Sipariş kartlarında "sipariş kodu - ürün modelleri", ürün kartlarında "ürün modeli + İEN" biçiminde. İEN yazımı değişiyor ("İEN:", "(İEN: …)", "İEN …").

**Kontrol listesi maddeleri** dört türden:

- **Adetli ürün satırları** ("1X ürün kodu ürün adı (İEN:…)"): 540 madde. Sipariş kartında siparişin içindeki ürünler böyle listeleniyor.
- **Bilgi maddeleri:** Motor Seri No (86), Kabin Rengi (29), İEN, yağ türü (yağlı sevk ve yağ adı, ya da yağsız sevk), konum ("İmalat Fabrikasında (tarih)", "Montaj Fabrikasında (tarih)").
- **"Yapıldı mı?" soruları:**
  - Motor Açılışı Tamamlandı mı? (33)
  - Metal Etiket Yapıştırıldı mı? (üç farklı yazımla, 29)
  - Pompa Montajı Tamamlandı mı? (10)
  - Uzaktan Erişim Modülü Bağlandı mı? (5)
  - Kablosuz Kumanda Seti Bağlandı mı? (5)
- **Diğer serbest maddeler.**

Aynı madde farklı yazımlarla geçiyor ("Metal Etiket / Metal Etiketi / Metal Etiketler Yapıştırıldı mı?"). Yeni sistemde bunlar sabit şablon maddeleri olur.

**Notlar alanı.** Serbest metin, ama çoğunlukla "anahtar: değer" satırlarından oluşuyor.

- En sık geçen anahtarlar: İEN (360), Sipariş No (332), Çene No (yaklaşık 200), Şanzıman (Seri) No (yaklaşık 160), Motor Seri No (39), Seri No (23); daha seyrek olarak Etiket Seri No, Şasi No, Renk.
- Yazımlar tutarsız: büyük-küçük harf, boşluk, "No" ya da "Numarası".
- Tarih içeren not satırı çok az (19). Tarihli ilerleme notları sohbette tutulmuş.

**Aktarım için anlamı.** Kart, kutu, durum, etiketler, kişiler, tarihler, kontrol listesi maddeleri ve notlar aktarılabilir. Notlardaki ve kontrol listesindeki İEN, sipariş no ve seri no'lar ayrıştırılıp ERP kayıtlarıyla eşleştirilebilir. Sohbet ve ekler bu dosyadan gelmez.

## 3. Yapı önerisi (taslak; uygulama planıyla kesinleşir)

- Planner'ın pano mantığını taşıyan, verisini ERP'den alan ayrı bir web uygulaması. Fabrikanın iç ağında çalışır; bilgisayardan ve telefondan tarayıcıyla açılır. Teknolojisi ve kurulumu eski portalla aynı ailedendir (Python, SQLite, Docker; bat dosyasıyla başlatma); kodu ve veritabanı ayrıdır.
- Kartı ERP olayları açar ve aşamasını değiştirir. Montaj ve test gibi fiziksel aşamaları ekip elle ilerletir.
- Her ürünün bir zaman akışı olur: ekibin notları ve ERP'den gelen olaylar ("iş emri açıldı", "ERP'de tamamlandı") tarih sırasıyla aynı akışta görünür. Planner'daki görev sohbetinin karşılığıdır.
- Kontrol listesindeki bilgiler (seri no, RAL, yağ…) ayrı alanlar olur; "yapıldı mı?" soruları kontrol maddesi olarak kalır.
- **Veri kaynağı katmanı.** ERP verisini getiren kısım uygulamanın geri kalanından ayrıdır. Bugün buraya Excel yüklemesi, ileride doğrudan ERP bağlantısı takılır. Uygunsuzluk ve DÖF uyarıları da sonradan aynı biçimde, iş emri numarasıyla bağlanan bir "uyarı kaynağı" olarak eklenir.
- **Elenen seçenek:** Planner'da kalıp ERP'den Planner'ı güncelleyen bir köprü. IT'den Microsoft 365 izni gerekir ve Planner'a kendi alanlarımız (seri no, uygunsuzluk uyarısı) eklenemez. Ayrı uygulamada ise Teams bildirimleri olmaz (soru 7).

## 4. Açık sorular

Cevaplanan soru 5. bölüme taşınır; numaralar değişmez.

**Başlangıç**

1. ~~Yeni repo nerede?~~ Cevaplandı (5. bölüm).

**Kapsam**

2. Hangi ürünler takip edilecek? Etiketlerde 10 ürün grubu var (2.1): hepsi mi takip edilecek? KCN ve SCN ne demek? Anlamı bilinmeyen etiketler ne anlatıyor: ".V" (299 kart), DKM, BGM? Bakım ve onarım işleri bu uygulamaya girecek mi?
3. "Ürün bazında" derken bir kart bir fiziksel ürün mü demek? 2 adetlik bir siparişe 2 kart mı açılıyor? Sipariş kartının kontrol listesinde siparişteki ürünler "1X ürün (İEN:…)" diye sıralanıyor ve Siparişler kutusunda 130 tamamlanmış kart var. Sipariş kartı, ürünlerin kartları açılınca mı tamamlanıyor?
4. Kutular ve geçişler. Dışa aktarımda görülen: STOK etiketli kartlar da sipariş kartlarıyla aynı kutulardan geçiyor; altıncı kutuda ("Üretilmesi planlanan veya Üretilen Yarı Mamüller") yalnızca 6 kart var ve hepsi tamamlanmış. Öneri:

   | Olay | Kartın gideceği kutu | Nasıl |
   |---|---|---|
   | Sipariş geldi, iş emri yok | Siparişler | ERP'den |
   | Siparişe bağlı iş emri açıldı | Malzemeler hazırlık | ERP'den |
   | Siparişe bağlı olmayan stok iş emri açıldı | Malzemeler hazırlık, "STOK" işaretiyle | ERP'den |
   | Montaja başlandı | Montajı devam edenler | Elle |
   | Son montaja ve teste geçildi | Son montaj & test | Elle |
   | İş emri ERP'de tamamlandı | Sevke hazır / Stok | ERP'den |
   | Sevk edildi | Tamamlandı | Soru 9'a bağlı |

   Yarı mamul kutusu hâlâ kullanılıyor mu, yeni sistemde kalsın mı?
5. Kontrol listeleri bugün standart değil: aynı madde farklı yazılıyor, kartların bir kısmında hiç yok (2.1). Her ürün grubu için sabit bir şablon belirleyelim mi? PP için öneri:
   - alanlar: motor seri no, kabin rengi, yağ
   - kontrol maddeleri: motor açılışı, metal etiket, pompa montajı, uzaktan erişim modülü, kablosuz kumanda
6. Karttaki son tarih siparişin sevk tarihi mi, montaj hedefi mi? Dışa aktarımda yalnızca 104 kartta dolu. Sevk tarihiyse ERP'den kendiliğinden dolabilir.
7. Uygulamayı kimler, kaç kişi kullanacak? Planda bugün 5 kişi var. Kim değişiklik yapacak, kim yalnızca bakacak? Telefondan kullanım ve "kart size atandı" gibi Teams bildirimleri ne kadar önemli?

**ERP verisi**

8. Eski projede kullanılan iki ERP raporunun (iş emirleri listesi, sipariş satırları listesi) yapı bilgisi kullanılabilir mi? Kod kopyalanmaz, yalnızca raporların yapısı kullanılır. Bu kez raporlar takip edilen bütün ürünler için alınır.
9. Sevkiyat ERP'de nereden anlaşılıyor: sipariş satırlarındaki "Ürün durumu"ndan mı, irsaliye ya da sevk raporundan mı?
10. "Sipariş talebi" ERP'de satış siparişinin kendisi mi (örneğin durumu "Beklemede" olan sipariş), yoksa siparişten önce açılan ayrı bir belge mi?
11. İş emrinin hangi siparişe ait olduğu ERP'de yalnızca açıklamaya mı yazılıyor, yoksa raporda ayrı bir "sipariş no" sütunu çıkarılabiliyor mu? Ayrı sütun varsa eşleştirme çok daha güvenilir olur.
12. ERP bağlantısı geldiğinde de yalnızca okunacak, ERP'ye hiçbir şey yazılmayacak; doğru mu?

**Geçmiş veri**

13. Dışa aktarımda Şubat 2025'ten bu yana 638 kart var, 500'ü tamamlanmış. Hepsi aktarılsın mı, yoksa belli bir tarihten sonrası mı? Planner bir süre yeni uygulamayla birlikte kullanılacak mı, geçiş tek seferde mi olacak? Kontrol listesi kısmen işaretli 63 kartta hangi maddenin yapıldığı bilinmiyor. Bu maddeler "bilinmiyor" olarak mı aktarılsın, yoksa açık kartlarda ekip bir kez gözden mi geçirsin?
14. Görev sohbeti dışa aktarımda yok. Seçenekler:
    - (a) Eski sohbetler Planner'da arşiv olarak kalır; açık kartların (138) önemli notları yeni uygulamaya elle girilir.
    - (b) Sohbetler Microsoft'un programlama arayüzüyle (Graph) okunmaya çalışılır. IT izni gerekir ve yeni Planner sohbetinin bu yolla okunup okunamadığı belirsiz.
    - (c) Sohbetler hiç aktarılmaz.

    Öneri: (a).

## 5. Kararlar

| Tarih | Konu | Karar |
|---|---|---|
| 19/10/2026 | Repo | GitHub'da `baristopal1808/OMS-Montaj` (private; 20/10/2026'ya kadar adı OMS-PLANNER'dı); bilgisayarda `Desktop\OMS Montaj`. Klasör taşınmaz, adı değiştirilmez; Claude'un hafızası ve sohbet geçmişi klasörün yoluna bağlıdır. |
| 19/10/2026 | Gerçek veri | `OMS Veri/` klasöründe durur (eski projeyle aynı ad; kullanıcı onayladı), git'e hiç girmez. |
| 19/10/2026 | Planner dışa aktarımı | `OMS Veri/planner/OMS İCİN VERİ.xlsx` doğru dosya (kullanıcı onayladı); yapısı 2.1'de. |
| 19/10/2026 | Gerçek adlar | Müşteri ve çalışan adları `OMS Veri/yasakli-kelimeler.txt` listesinde kalır ve git'e giren hiçbir dosyada geçmez. Uygulama çalışırken gerçek veriden gelen adları (atanan kişi, müşteri) ekranda aksamadan gösterir (kullanıcı teyit etti, 20/10/2026). |
| 19/10/2026 | Veri yedeği | `OMS Veri/` sunucuya yedeklenir (`yedekle.bat`, `/kaydet`). 20/10/2026: kullanıcı kararıyla şimdilik ertelendi; araç hazır, `yedek-hedefi.txt` yazılınca çalışır. Aday klasör kullanıcının sunucudaki kişisel klasörü (Ortak_Alan altında; başkalarının görüp göremediği netleşmeli). |
| 19/10/2026 | Oturum düzeni | `/devam`, `/kaydet`, oturum açılış hatırlatması, git kapı bekçisi ve Claude koruması kuruldu (CLAUDE.md, Korumalar). `/kaydet` yazmak commit ve push onayıdır. |
