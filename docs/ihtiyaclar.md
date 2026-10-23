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

## 2. Planner'dan anlaşılanlar (kullanıcı onayladı, 21/10/2026; denemelerde aksi söylenmedikçe geçerli)

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
| Ürün ailesi | .V (299): Vibrohammer; OVR ve SVR modellerinde kullanılır |
| Kaynak | SİPARİŞ (420), STOK (127), SICAK SIPARİŞ (18), YEDEK PARCA (14) |
| Durum | SEVKE HAZIR (44), Test Aşamasında (4), Volvo Bekleniyor (1) |
| İş türü | Motor Pompa Hattı (18), Yarı Mamül (13), Bakım & Onarım (6), SG CENE (2), PP Pompa Montajı (1) |
| Alt montaj | DKM (27): dişli kutusu montajı; BGM (4): balans grubu montajı |

Anlamlar (kullanıcı, 20/10/2026):

- **SCN ve KCN:** OVR-S, OVR-SG, SVR-NF ve SVR-VM'ye bağlanan hidrolik çeneler. Sipariş taleplerinde en az bir çene, bazen ikisi birden bulunur.
- **DKM (dişli kutusu montajı):** OVR ve SVR modellerinin alt montajı; montajın yaklaşık yarısını kapsar.
- **BGM (balans grubu montajı):** dişli kutusu montajında kullanılan alt montaj.

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

### 2.2 Sipariş talebi formu (20/10/2026 incelemesi)

Kaynak: kullanıcının sohbette paylaştığı dört sipariş talebi görüntüsü (`OMS Veri/erp/` klasöründe): iki makine, bir servis, bir yedek parça. Form ERP'den çıkıyor. Burada yalnızca yapı var.

- **Üst kısım:** tarih (talebin onaylanıp sisteme girildiği gün), sayfa; sipariş no (proje kodu biçiminde), sipariş tipi, teslim tarihi (müşteriyle anlaşılan son sevk tarihi).
- **Sipariş tipi üç tane:** makine, yedek parça, servis.
- **Satırlar:** ürün kodu, ürün adı, miktar, seri no, açıklama.
- **Alt kısım:** serbest bir "Not" alanı ve talebi veren ile alan kişilerin adları.

**Makine talebi**

- **Seri no talep anında veriliyor:** "<sipariş no>-<tür>-<sıra>" biçiminde. Türler VH (vibrohammer), PP (güç ünitesi), HC (hidrolik çene). 2 adetlik satırda iki seri no yazılı.
- **Kiriş satırı:** seri no'su yok. Ürün adında kirişin hangi vibrohammer modeli için olduğu yazıyor; bazen çene modeli de yazıyor.
- **Kablosuz kumanda seti ve uzaktan erişim modülü:** kendi ürün kodlarıyla ayrı satır.
- **Aksesuar satırları:** seri no'suz (örneğin hortum seti).
- **Renk:** vibrohammer satırının açıklamasında "Renk: …".
- **Yağ:** PP satırının açıklamasında; yazımı değişiyor: "yağsız sevk edilecektir", "<yağ adı> yağlı sevk" ya da yalnızca yağın adı ("<yağ adı> - Hidrolik Yağ"). Bazen hiç yazmıyor.

**Servis talebi.** Satırlar bakım-onarım ürün kodları (kodun sonunda "-MNT"; örneğin güç ünitesi ve vibro çakıcı bakım-onarımı). Seri no sütunu boş; bakımı yapılacak makinelerin seri no'ları Not alanında serbest metinle yazıyor. Eski makinelerin seri no'su yalnızca sayıdan oluşabiliyor.

**Yedek parça talebi.** Çok sayıda parça satırı, adetleri yüksek, seri no yok. Nakliye gibi hizmet satırları da var.

### 2.3 ERP örnek dosyaları (20/10/2026 incelemesi)

Dosyalar `OMS Veri/erp/` klasöründe. Burada yalnızca yapı ve sayılar var. Dosyalar eski Excel biçiminde (.xls); yalnızca çıkış yapılamayan malzeme raporu .xlsx. Tarihlerin çoğu Excel gün sayısı olarak geliyor.

| Dosya | Boyut | İçerik |
|---|---|---|
| Sipariş talepleri | 136 satır, 37 sipariş, 115 sütun | Açık siparişlerin satırları; her satır bir sipariş kalemi |
| Siparişi tamamlanan sipariş talepleri | 283 satır, 94 sipariş | Aynı rapor, kapalı siparişler |
| Açık iş emirleri | 227 satır, 83 iş emri, 75 sütun | Her iş emrinin alt satırları var (sıra no) |
| Kapalı iş emirleri listesi | 1.316 satır, 471 iş emri, 75 sütun | Açık iş emirleriyle aynı biçim; kapatma tarihleri Temmuz 2024'ten başlıyor |
| Çıkış yapılamayan malzeme | 3.305 satır, 26 sütun | Açık iş emirlerinin malzeme satırları |
| Stok raporları: montaj depo, montaj üretim depo, sevk depo | her biri yaklaşık 7.700 satır, 17 sütun | Bütün malzemeler; miktarı 0'dan büyük olan 2.306 / 26 / 52 |

**Sipariş talepleri listesi**

- Formun (2.2) bilgileri satır satır var: sipariş no ve sıra no, ürün kodu ve adı, miktar, sevk edilen miktar ve bakiye, uzlaşılan sevk tarihi, onay tarihi, açıklama (renk, yağ), sipariş açıklaması (formdaki "Not").
- Seri no'lar "Planlama Bilgisi" sütununda; birden çok adet varsa " & " ile ayrılmış.
- "Bağlı İşemri No" bazı satırlarda dolu: açık listede 31/136, tamamlanan listede 90/283.
- Sipariş durumu: açık listede Onaylı, Beklemede, İptal; tamamlanan listede Kapalı.
- Sipariş detay türü formdaki sipariş tipidir: MAKİNA, YEDEK P., SERVİS. İptal satırlarda boş.
- ERP'nin kendi "Ürün Durumu" sütunu var: İmalatta, Montajda, Hazır, Sevke Hazır.
- Tamamlanan listede ilk ve son sevk tarihi dolu.
- Müşteri adı ve satış temsilcisi de var (uygulama ekranda gösterebilir; belgelere yazılmaz).

**Açık iş emirleri**

- Her iş emrinin sıra no 0 satırı ana üründür; diğer sıralar alt montajlar ve işlemlerdir (dişli kutusu, balans, hortum hatları, kumlama, astar, boya, PP alt montajları…). Bir iş emrinde 100'den fazla alt satır olabiliyor.
- Dişli kutusu ve balans montajları çoğunlukla ana makinenin iş emrinin alt satırı; bazen stok için ayrı iş emri. Motor-pompa hattı ayrı iş emri.
- Kaynak tipi: Montaj, Üretim, Bakım-Onarım. Envanter tipi: Son Ürün, Yarı Mamul.
- Proje bağlantısı: dolu 169 açıklamanın 136'sında proje kodu geçiyor ("… projesi için üretilecektir" gibi; yazımı değişiyor), 32'sinde "stok" geçiyor. "Sip. No" sütunu 76 satırda dolu, gerisinde "---".
- PP iş emirlerinin açıklamasında motor seri no'ları da yazılabiliyor.
- Planlanan, gerçekleşen ve kalan miktar; açılış, başlama ve tahmini bitiş tarihi; ilk ve son stok giriş tarihi var.
- Tamamlanmış iş emirleri ayrı dosyada (kapalı iş emirleri listesi). Orada kapatma tarihi ve ilk/son stok giriş tarihi neredeyse her satırda dolu; açıklamaların çoğunda proje kodu, bir kısmında "stok" geçiyor. Birkaç kapatma tarihi ileri bir güne düşüyor.

**Çıkış yapılamayan malzeme raporu**

- Başlığı "Montaj açık iş emri raporu"; açık iş emirlerinin bütün malzeme satırlarını veriyor. 906 satırda planlanan takip miktarı gerçekleşen çıkıştan büyük (217 iş emri/sıra).
- Malzemenin her depodaki miktarı da var (ana ürün, üretim, montaj, montaj üretim, sevk).
- İş emri no "no / sıra" biçiminde tek sütunda; iş emri açıklaması ve rota da var.

**Stok raporları**

- Her depo ayrı dosya; dosyada depo kodu boş, depo dosyadan anlaşılıyor.
- Bütün malzemeler listeleniyor, çoğunun miktarı 0. Bitmiş ürünler montaj üretim deposunda (26 kalem) ve sevk deposunda (52 kalem); montaj deposunda çoğunlukla parça var.

**Ürün kodu önekleri**

- SVR, OVR, OVF, WD, PP, SCN, KCN: ürün aileleri. Sonu "-MNT" ile biten kod bakım-onarımdır.
- CB: kiriş. CP ve P: yarı mamul ve alt montajlar (P: PP alt montajları). Sonu "-HH" ile biten: hidrolik hortum seti.
- OZ: malzeme ve aksesuar; "OZ-<proje>-PR-0x" biçimindeki kodlar projeye özel ürün (bağlantı çatalı, uzatma bomu, mandrel…).

## 3. Yapı önerisi (taslak; uygulama planıyla kesinleşir)

- Planner'ın pano mantığını taşıyan, verisini ERP'den alan ayrı bir web uygulaması. Fabrikanın iç ağında çalışır; bilgisayardan ve telefondan tarayıcıyla açılır. Teknolojisi ve kurulumu eski portalla aynı ailedendir (Python, SQLite, Docker; bat dosyasıyla başlatma); kodu ve veritabanı ayrıdır.
- Kartı ERP olayları açar ve aşamasını değiştirir. Montaj ve test gibi fiziksel aşamaları ekip elle ilerletir.
- Her ürünün bir zaman akışı olur: ekibin notları ve ERP'den gelen olaylar ("iş emri açıldı", "ERP'de tamamlandı") tarih sırasıyla aynı akışta görünür. Planner'daki görev sohbetinin karşılığıdır.
- Kontrol listesindeki bilgiler (seri no, RAL, yağ…) ayrı alanlar olur; "yapıldı mı?" soruları kontrol maddesi olarak kalır.
- **Veri kaynağı katmanı.** ERP verisini getiren kısım uygulamanın geri kalanından ayrıdır. Bugün buraya Excel yüklemesi, ileride doğrudan ERP bağlantısı takılır. Uygunsuzluk ve DÖF uyarıları da sonradan aynı biçimde, iş emri numarasıyla bağlanan bir "uyarı kaynağı" olarak eklenir.
- **Elenen seçenek:** Planner'da kalıp ERP'den Planner'ı güncelleyen bir köprü. IT'den Microsoft 365 izni gerekir ve Planner'a kendi alanlarımız (seri no, uygunsuzluk uyarısı) eklenemez. Ayrı uygulamada ise Teams bildirimleri olmaz (soru 7).

### 3.1 Aşamalar (soru 4; denemelerde kesinleşir)

Aşamaların adı ve sırası Ayarlar'dan düzenlenir.

**Son ürün** (vibrohammer, PP, çene, kiriş…)

| Aşama | Kart buraya nasıl gelir |
|---|---|
| Sipariş | ERP: sipariş talebi geldi, iş emri henüz yok |
| Malzeme hazırlık | ERP: iş emri açıldı (siparişe bağlı ya da stok) |
| Montaj | Elle |
| Teste hazır | Elle |
| Test | Elle |
| Temizlik | Elle |
| Sevke hazır | Elle; temizlik ve motor açılışı yapılınca |
| Sevk edildi | Elle, irsaliye sonrası (soru 9) |

- **Stok için yapılan ürün** montaj bitince "Stokta" aşamasına geçer (Planner'daki "Sevke hazır / Stok"). Test edilmediyse kartında "Test bekliyor" uyarısı olur. Siparişe atanınca kalan aşamalardan devam eder: test edilmediyse teste, sonra temizliğe.
- **İş emrinin ERP'de tamamlanması** kartı kendiliğinden taşımaz; zaman akışında olay olarak görünür. Ürün sevk deposunda değilse uygulama "Testi yapıldı mı?" diye sorar.
- **Motor açılışı** kontrol maddesi olarak kalır; "Volvo açılış için bekleniyor" bekleme etiketidir. Motor açılışı işaretlenmemiş kart sevke hazıra geçirilmek istenirse uygulama uyarır.

**Yarı mamul** (DKM, BGM, motor-pompa hattı): Malzeme hazırlık → Montaj → Hazır. Makineye takılınca kart kapanır. Planner'daki yarı mamul kutusu ayrıca gerekmez; yarı mamuller filtreyle ayrılır.

### 3.2 ERP raporları (soru 8)

Uygulama ERP'den yalnızca okur. Örnekler `OMS Veri/erp/` klasöründe; yapıları 2.3'te.

| Rapor | Ne için | Örnek |
|---|---|---|
| Sipariş talepleri (açık) | Sipariş ve ürün kartları; seri no, teslim tarihi, renk, yağ, aksesuar | Var |
| Siparişi tamamlanan sipariş talepleri | "Sevk edildi, kartı kapatayım mı?" | Var |
| Açık iş emirleri | Kartın malzeme hazırlığa geçmesi, bağlantı, alt montajlar | Var |
| Kapalı iş emirleri | İş emrinin ERP'de tamamlanması | Var |
| Çıkış yapılamayan malzeme | Açık kalem uyarısı | Var |
| Stok raporları (montaj depo, montaj üretim depo, sevk depo) | İlk stok kaydı, "depoda stok mevcut", test sorusu | Var |

Uygulamanın .xls ve .xlsx dosyalarını okuyabilmesi için Python'a Excel okuma kütüphaneleri eklenmesi gerekecek. Uygulama planında onaya sunulur.

## 4. Açık sorular

Cevaplanan soru 5. bölüme taşınır; numaralar değişmez.

**Başlangıç**

1. ~~Yeni repo nerede?~~ Cevaplandı (5. bölüm).

**Kapsam**

2. ~~Hangi ürünler takip edilecek?~~ Cevaplandı (5. bölüm).
15. ~~Etiketlerin yapısı~~ Cevaplandı (5. bölüm).
3. ~~Kart ve ürün ilişkisi~~ Cevaplandı (5. bölüm).
16. ~~Bağlama ayrıntıları~~ Cevaplandı (5. bölüm).
18. ~~Kirişler~~ Cevaplandı (5. bölüm).
4. ~~Aşamalar ve geçişler~~ Cevaplandı (5. bölüm; aşama listesi 3.1'de).
5. ~~Kontrol listesi şablonları~~ Cevaplandı (5. bölüm).
22. Vibrohammer ailesinin (SVR, OVR) ve diğerlerinin (OVF, WD, çene, kiriş, DKM, BGM, motor-pompa hattı) şablonları. Kullanıcı kararıyla ileriye bırakıldı. Kesin olan: vibrohammer'da "Metal etiket yapıştırıldı mı?" maddesi. Başlangıç önerisi: her son üründe seri no alanı, çenede çene no, motor-pompa hattında motor seri no; gerisi Ayarlar'dan eklenir. Planner notlarında sık geçen bilgiler: çene no, şanzıman (seri) no, motor seri no, etiket seri no, şasi no, renk.
23. ~~Motor eksperi~~ Cevaplandı (5. bölüm).
24. ~~Sipariş talebi formu~~ Cevaplandı (5. bölüm).
25. ~~Yedek parça siparişi~~ Cevaplandı (5. bölüm).
26. ~~Servis siparişi~~ Cevaplandı (5. bölüm; denemelerde çalışılacak).
6. ~~Karttaki son tarih~~ Cevaplandı (5. bölüm).
7. ~~Kullanıcılar ve yetkiler~~ Cevaplandı (5. bölüm).
28. ~~Ana ekran ve pano~~ Cevaplandı (5. bölüm).
34. ~~Kart olan satırlar~~ Cevaplandı (5. bölüm).
35. ~~Yazı boyutu~~ Cevaplandı (5. bölüm).

**ERP verisi**

8. ~~ERP raporları~~ Cevaplandı (5. bölüm; rapor listesi 3.2'de).
9. ~~Sevkiyat~~ Cevaplandı (5. bölüm).
10. ~~Sipariş talebi ERP'de nedir?~~ Cevaplandı: ERP'deki sipariş talebi belgesi; formu Excel olarak alınır (5. bölüm, soru 24b ve 27).
11. ~~İş emri ile sipariş bağlantısı~~ Cevaplandı (5. bölüm).
12. ~~ERP'ye yazma~~ Cevaplandı (5. bölüm).
17. ~~Açık kalem raporu~~ Cevaplandı (5. bölüm).
19. ~~Çene no ve stoğa alınış tarihi~~ Cevaplandı (5. bölüm).
20. ~~Ürünün hangi depoda olduğu~~ Cevaplandı (5. bölüm).
29. ~~Toplu liste~~ Cevaplandı (5. bölüm).
30. ~~Beklemede siparişler~~ Cevaplandı (5. bölüm).
31. ~~ERP ürün durumu~~ Cevaplandı (5. bölüm).
32. ~~Tamamlanan iş emirleri~~ Cevaplandı (5. bölüm).
33. ~~Eksik miktar~~ Cevaplandı (5. bölüm).
43. Sipariş talepleri listesinde satırların bir kısmı yok: 131 siparişin 32'sinde satır numaraları atlıyor, toplam 151 satır listede değil (21/10/2026 denemesi). Açık listedeki bütün satırların "İmalat Türü" "Son Ürün"; liste alınırken bu süzgeç uygulanmış olabilir. Bu yüzden satın alınan kalemler (kablosuz kumanda seti, uzaktan erişim modülü, hortum seti…) listeye girmiyor; PP'nin koşullu kontrol maddeleri ve aksesuar listesi bunlara bağlı. Liste süzgeçsiz (bütün imalat türleriyle) alınabilir mi? Uygulama atlanan satırları yüklemede ve sipariş kartında bildiriyor.
21. ~~Kablosuz kumanda, uzaktan erişim ve yağ sipariş talebinde nasıl yazılıyor?~~ Cevaplandı (5. bölüm).
27. ~~Sipariş talebinin Excel hali~~ Cevaplandı (5. bölüm).

**Geçmiş veri**

13. ~~Geçmiş Planner kartları~~ Cevaplandı (5. bölüm).

**Plandan önce**

36. ~~Kişi atama~~ Cevaplandı (5. bölüm).
37. ~~Öncelik~~ Cevaplandı (5. bölüm).
38. ~~Görünümler~~ Cevaplandı (5. bölüm).
39. ~~Uygulamanın çalışacağı yer~~ Cevaplandı (5. bölüm).
40. ~~Atamanın kalanı ve müdürlerin yetkisi~~ Cevaplandı (5. bölüm).
41. ~~Sunucu kurulumu~~ Cevaplandı (5. bölüm). Sunucunun işletim sistemi kurulum adımında öğrenilecek.
42. ~~Hata bildiriminin WhatsApp'a nasıl gideceği~~ Cevaplandı (5. bölüm).
14. ~~Görev sohbeti~~ Cevaplandı (5. bölüm).

## 5. Kararlar

| Tarih | Konu | Karar |
|---|---|---|
| 19/10/2026 | Repo | GitHub'da `baristopal1808/OMS-Montaj` (private; 20/10/2026'ya kadar adı OMS-PLANNER'dı); bilgisayarda `Desktop\OMS Montaj`. Klasör taşınmaz, adı değiştirilmez; Claude'un hafızası ve sohbet geçmişi klasörün yoluna bağlıdır. |
| 19/10/2026 | Gerçek veri | `OMS Veri/` klasöründe durur (eski projeyle aynı ad; kullanıcı onayladı), git'e hiç girmez. |
| 19/10/2026 | Planner dışa aktarımı | `OMS Veri/planner/OMS İCİN VERİ.xlsx` doğru dosya (kullanıcı onayladı); yapısı 2.1'de. |
| 19/10/2026 | Gerçek adlar | Müşteri ve çalışan adları `OMS Veri/yasakli-kelimeler.txt` listesinde kalır ve git'e giren hiçbir dosyada geçmez. Uygulama çalışırken gerçek veriden gelen adları (atanan kişi, müşteri) ekranda aksamadan gösterir (kullanıcı teyit etti, 20/10/2026). |
| 19/10/2026 | Veri yedeği | `OMS Veri/` sunucuya yedeklenir (`yedekle.bat`, `/kaydet`). 20/10/2026: kullanıcı kararıyla şimdilik ertelendi; araç hazır, `yedek-hedefi.txt` yazılınca çalışır. Aday klasör kullanıcının sunucudaki kişisel klasörü (Ortak_Alan altında; başkalarının görüp göremediği netleşmeli). |
| 19/10/2026 | Oturum düzeni | `/devam`, `/kaydet`, oturum açılış hatırlatması, git kapı bekçisi ve Claude koruması kuruldu (CLAUDE.md, Korumalar). `/kaydet` yazmak commit ve push onayıdır. |
| 20/10/2026 | Takip kapsamı | Etiketlerdeki 10 ürün grubunun hepsi takip edilir; alt montajlar (DKM, BGM), yedek parça ve bakım-onarım işleri de. Etiketlerin anlamları 2.1'de. |
| 20/10/2026 | Etiketleri kullanıcı yönetir | Kullanıcı etiketleri uygulamanın içinden ekler ve adlarını değiştirir. Bu yalnızca ürün grupları için değil; sevke hazır, teste hazır, Volvo açılış için bekleniyor, temizlik aşamasında, sipariş, bakım-onarım gibi etiketler için de geçerlidir. Yapı önerisi: soru 15. |
| 20/10/2026 | Filtre | Kartlar montaj grubuna göre (OVR, SVR, PP…) filtrelenip görüntülenebilmeli. |
| 20/10/2026 | Etiket yapısı (soru 15) | Etiketler gruplanır (ürün grubu, kaynak, iş türü, bekleme) ve Ayarlar'dan yönetilir. Adı değişen etiket bütün kartlarda yeni adla görünür; kullanılmayan etiket silinmez, pasif yapılır. Ürün grubu iki basamaklıdır: aile (PP, SVR, OVR, OVF, WD, Çene) ve model. Planner'daki numaralar yalnızca sıralama içindi; adlara numara eklenmez, sıra Ayarlar'dan verilir. ".V" etiketi kalkar; SVR ile OVR'nin hepsi vibrohammer (vibroçakıcı) ailesindedir ve bunları birlikte gösteren hazır bir "Vibrohammer" filtresi olur. |
| 20/10/2026 | Elle ilerleyen aşamalar | Teste hazır, temizlik ve sevke hazır etiket değil, aşamadır. Ekip gözleme dayanarak elle ilerletir; ERP'de karşılıkları yoktur. Temizlik ve motor açılışı yapılınca ürün sevke hazır olur. Aşama listesini kullanıcı Ayarlar'dan düzenler. |
| 20/10/2026 | Bağlı kartlar (soru 3'ün bir kısmı) | Çene (SCN, KCN), dişli kutusu montajı (DKM), balans grubu montajı (BGM) ve PP'nin motor-pompa hattı ayrı kartlarla izlenir. DKM, BGM ve motor-pompa hattı yarı mamuldür; çene ise vibrohammer ve powerpack gibi son üründür. Ana ürünün kartında bağlı kartların durumu görünür ("Çene: hazır", "Motor-pompa hattı: hazır"). |
| 20/10/2026 | Bir kart bir ürün (soru 3) | Her fiziksel ürünün ayrı kartı olur; 2 adetlik siparişe 2 kart açılır. Bağlı kart son aşamasına gelince ana kartta "Hazır" yazar; öncesinde bulunduğu aşama yazar. |
| 20/10/2026 | Bağlantı kuralı (soru 3) | ERP'de bağlantı varsa kartlar kendiliğinden bağlanır (PP alt montajları ERP'de her zaman projeye bağlanıyor). Bağlantı yoksa (vibro tarafında iş emri bazen stok olarak açılıyor) uygulama kendisi bağlamaz, kullanıcıya sorar. Adaylar iş emri no ve açılış tarihiyle listelenir. İş emrinde depodan çıkışı yapılmamış malzeme (açık kalem) varsa o da gösterilir ve sorulur: "5 adet cıvatanın çıkışı yapılmamış, bilginiz var mı?" Ayrıntılar: soru 16 ve 17. |
| 20/10/2026 | Stok eşleştirme (soru 16) | (1) Bağlantısız bir stok iş emri tamamlanınca, aynı ürünü bekleyen bir sipariş varsa uygulama bağlamayı sorar. (2) Yeni sipariş yüklenince, depoda aynı üründen stok varsa ürünün yanında "depoda stok mevcut" ibaresi çıkar. Stokların çene no'su, iş emri açılış tarihi ve stoğa alınış tarihi listelenir; atamayı kullanıcı yapar. Çene no ve stoğa alınış tarihi uygulamadaki stok kaydından, iş emri açılış tarihi İEN girilmişse ERP'den gelir (soru 19). |
| 20/10/2026 | Çene ve kiriş (soru 16) | Çene siparişe değil, belirli bir vibrohammer'a bağlanır. Montajda kiriş SVR'ye, çeneler kirişe bağlanır. SVR ürünlerinde çeneler demonte sevk edilir. Kirişin takibi: soru 18. |
| 20/10/2026 | Açık kalem raporu (soru 17) | ERP'den alınabilir: rapor, çıkış yapılamayan malzemeyi iş emri ve eksik miktarla gösterir. |
| 20/10/2026 | Kirişler (soru 18) | Kirişler ürünlerden bağımsız iş emriyle yapılır ve müşteri talebine göre eklenir. Standart değildir: 6-7 farklı kiriş montajı var ve her kiriş her vibrohammer'a uymaz. Hangi kirişin istendiği sipariş talebinden izlenir. |
| 20/10/2026 | Seri numaraları (soru 19) | Çene no, motor-pompa hattındaki Volvo motorunun seri no'su ve son ürünlerin seri no'su iş emri tamamlanırken yazılır; ürün seri no'suyla stoğa alınır. ERP bunları bugün tek tek veremiyor (değişirse kullanıcı haber verecek). Bu yüzden seri no'lar uygulamada tutulur: ürün stoğa alınırken ekip İEN'yi ve seri/çene no'yu uygulamaya girer. |
| 20/10/2026 | İlk stok kaydı (soru 19) | Sistemin oturması için eldeki stoklar bir kez kaydedilir. Kullanıcı ERP stok raporunu verir; uygulama malzemeyi, depo konumunu (sevk depo, montaj depo, montaj üretim depo…) ve adedi çıkarır, her adet için çene/seri no ve gerekirse İEN girilecek bir alan sunar. |
| 20/10/2026 | Kiriş ve çene görünümü (soru 18) | Kiriş ve çene vibrohammer kartında bağlı kart olarak görünür; şimdilik yeterli. Montajda kiriş SVR'ye, çene kirişe bağlanır. |
| 20/10/2026 | Aşamalar (soru 4) | Başlangıç listesi 3.1'deki gibidir; aşamalar denemelerde kesinleşir ve Ayarlar'dan düzenlenir. DKM, BGM ve motor-pompa hattı kartları makineye takılınca kapanır. |
| 20/10/2026 | Test edilmeden stok (soru 4) | Ürün test edilmeden stoğa alınabilir; özellikle OVR'ler. Müşteri yoksa test için powerpack ya da zaman olmayabiliyor. Müşteri talep edince ürün teste alınır, temizlenir, sevke hazır olur ve sevk edilir. Test edilmemiş ürünün kartında "Test bekliyor" uyarısı görünür. |
| 20/10/2026 | ERP tamamlaması (soru 4) | İş emri yüzde 90 oranında montaj bitince ERP'de tamamlanır; ürün sevk deposuna değil, montaj üretim deposuna alınır. Ürün sevk deposunda değilse uygulama "Testi yapıldı mı?" diye sorar; ürün cevaba göre stokta "test edildi" ya da "test bekliyor" olarak bekler. Depo bilgisinin kaynağı: soru 20. |
| 20/10/2026 | Kontrol listesi şablonları (soru 5) | Her ürün ailesinin, kullanıcının Ayarlar'dan düzenlediği bir şablonu olur: bilgi alanları ve "yapıldı mı?" maddeleri. Bir madde koşullu olabilir: yalnızca sipariş talebinde ilgili kalem varsa karta gelir. |
| 20/10/2026 | PP şablonu (soru 5) | Alanlar: PP seri no, kabin seri no (müşterinin verdiği), motor seri no, kabin rengi (RAL), yağ (yağlı sevk ve yağ türü, ya da yağsız sevk). Kontrol maddeleri: motor açılışı tamamlandı mı, motor eksper işlemi yapılacak mı, metal etiket yapıştırıldı mı, pompa montajı tamamlandı mı. Uzaktan erişim modülü ve kablosuz kumanda seti yalnızca sipariş talebinde varsa gelir. Ayrıntılar: soru 21 ve 23. |
| 20/10/2026 | Vibrohammer şablonu (soru 5) | İleriye bırakıldı (soru 22). Kesin olan: "Metal etiket yapıştırıldı mı?" maddesi. |
| 20/10/2026 | Motor eksperi (soru 23) | "Motor eksper işlemi yapılacak mı?" cevabı evetse kartta "Eksper bekleniyor" ibaresi çıkar. Kullanıcı eksper bölümünden "Eksper yapıldı"yı seçer; yapıldığı tarih görünür. Motor açılışıyla sırası fark etmez: test edilmiş ve motor açılışı yapılmış ürünün eksperi sonradan yapılabilir. Motor milli ise eksper yapılmaz. Eksperin yakında tamamen kalkması planlanıyor; madde Ayarlar'dan pasif yapılabilmeli. |
| 20/10/2026 | Tarihler (soru 6) | Kartın son tarihi müşteriyle anlaşılan son sevk tarihidir; yaklaşınca turuncu, geçince kırmızı görünür. Kartın açılış tarihi de bilgi olarak görünür. Kullanıcı montaja başlarken kartın notuna bilgi yazıyor; yeni sistemde bu notlar kartın zaman akışına yazılır. Son sevk tarihinin kaynağı: sipariş talebindeki teslim tarihi (soru 24c). |
| 20/10/2026 | Seri no ve çene no (soru 24a) | Sipariş talebindeki seri no (sipariş anında verilir, "<sipariş no>-HC-01" gibi) çene ürününün seri numarasıdır. Çene no ise çene montajında kullanılan parçanın numarasıdır ve iş emri tamamlanırken yazılır. İkisi farklıdır; kartta ayrı ayrı görünür. |
| 20/10/2026 | Sipariş talebinin kaynağı (soru 24b) | Sipariş talebi formu ERP'den çıkıyor. Kullanıcı formun Excel halini verecek; siparişler buradan okunur. |
| 20/10/2026 | Form tarihleri (soru 24c) | Sağ üstteki tarih, sipariş talebinin onaylanıp sisteme girildiği tarihtir. Teslim tarihi, müşteriyle anlaşılan son sevk tarihidir; kartın son tarihi buradan gelir. |
| 20/10/2026 | Aksesuarlar (soru 24d) | Hortum seti gibi aksesuarlar sipariş kartında listelenir. Aksesuar için ERP'de ayrı bir sipariş talebi açılıyor ve yanına hangi proje için ya da stok için istendiği not olarak yazılıyor; bu not ERP'den çekilemeyebilir. Aksesuar, ait olduğu proje ve ERP sipariş no ile izlenir. Takibin ayrıntısı: soru 24 (f). |
| 20/10/2026 | Yağ (soru 21) | PP satırının açıklamasında "yağsız sevk edilecektir", "<yağ adı> yağlı sevk" ya da yalnızca yağın adı yazıyor; bazen hiç yazmıyor. Uygulama yağ bilgisini açıklamadan okur. Yağ ibaresi yoksa kartta bilginin netleştirilmesini ister. |
| 20/10/2026 | Kablosuz kumanda ve uzaktan erişim (soru 21) | Sipariş talebinde kendi ürün kodlarıyla ayrı satır olarak geçiyor. Bu satırlar varsa PP kartına ilgili kontrol maddesi kendiliğinden eklenir. Hangi ürün kodunun hangi maddeyi getireceği Ayarlar'dan tanımlanır. |
| 20/10/2026 | Sipariş tipleri (soru 24e) | Üç tip var: makine, yedek parça, servis. Tip, kartın etiketini kendiliğinden verir: makine → sipariş, yedek parça → yedek parça, servis → bakım-onarım. |
| 20/10/2026 | Aksesuar takibi (soru 24f) | Şimdilik yeterli: sipariş kartında aksesuar satırının yanında ERP talep no ve durum (bekleniyor / hazır) görünür. Talep no ERP'den eşleşemezse kullanıcı yazar. Stok raporunda aynı ürün kodu varsa depodaki adet gösterilir. Denemelerde yeniden bakılır. |
| 20/10/2026 | Yedek parça siparişi (soru 25) | Sipariş başına tek kart açılır; parçalar kartın içinde liste olarak görünür. Aşamalar: Sipariş → Hazırlanıyor → Sevke hazır → Sevk edildi. Nakliye gibi hizmet satırları gösterilmez. |
| 20/10/2026 | Servis siparişi (soru 26) | Servis siparişi seyrek geliyor. Takibi denemelerde birlikte çalışılacak; kullanıcı görmek istediği verileri o zaman paylaşacak. Başlangıç taslağı: bakıma gelen her makine bir kart; seri no Not alanından okunur ya da elle yazılır; seri no kayıtlı bir makineye aitse servis kartı o makinenin geçmişine bağlanır. Aşamalar: Makine geldi → Bakım-onarım → Test → Sevke hazır → Sevk edildi. |
| 20/10/2026 | Sipariş talebinin Excel hali (soru 27) | ERP sipariş talebi formunu Excel olarak da veriyor. Soru 29 ile değişti: tek tek form yerine toplu sipariş talepleri listesi yüklenir. |
| 20/10/2026 | Kullanıcılar (soru 7a) | Uygulamayı Planner'daki 5 kişi kullanır; değişirse kullanıcı haber verir. |
| 20/10/2026 | Giriş ve yetkiler (soru 7b) | Herkes kendi kullanıcı adı ve şifresiyle girer; zaman akışında kimin ne yaptığı görünür. Deneme süresince yetki ayrımı yok, herkes her şeyi yapabilir. Yetkiler ileride kullanıcının isteğiyle kişi kişi tanımlanır; yapı buna hazır kurulur. |
| 20/10/2026 | Telefon ve fotoğraf (soru 7c) | Uygulama telefondan rahat kullanılmalı. Ürünle ilgili bir hata ya da bekleme durumu için karta fotoğraf eklenebilmeli; fotoğraf o karta aittir. Fotoğraflar gerçek veridir, git'e girmez. |
| 20/10/2026 | E-posta bildirimi (soru 7d) | Denemelerden sonra karar verilecek: hangi olayların kime e-postayla gideceği değerlendirilecek. |
| 20/10/2026 | Sipariş kartı ana kalemdir | Ana giriş noktası sipariş kartıdır. Sipariş kartında ürünler bölüm bölüm görünür (vibrohammer, PP, çene…); her ürünün içinde konuşulan her şey yer alır: aşama, kontrol listesi, seri no'lar, bağlı kartlar, notlar, fotoğraflar. ERP örnek Excel'lerinden gelen bilgiler de buraya işlenir. Ana ekran ve pano: soru 28. |
| 20/10/2026 | Sevk ve kapanış (soru 9) | ERP'de sipariş sevk edilip irsaliyeli çıkışı yapılınca "tamamlandı" gibi bir durum görünüyor; uygulama bunu okur. Kartı kendisi kapatmaz, "Sevk edildi, kartı kapatayım mı?" diye sorar. |
| 20/10/2026 | ERP'ye yazma (soru 12) | Şimdilik ERP'ye hiçbir müdahale yok; uygulama yalnızca okur. |
| 20/10/2026 | İş emri ile sipariş bağlantısı (soru 11) | İş emrinin hangi proje için açıldığı çoğunlukla iş emrinin açıklamasında yazıyor; uygulama bağlantıyı oradan okur. Siparişte bir ürün talebi varken ERP'de bağlantı görünmüyorsa uygulama sorar: örneğin aynı üründen farklı iş emirleriyle üretilmiş 3 adet varsa hangisinin siparişe ekleneceğini kullanıcı seçer. |
| 20/10/2026 | Örnek dosyalar (soru 8) | Eski projeye bakılmaz. Kullanıcı 3.2'deki raporların örnek Excel'lerini `OMS Veri/erp/` klasörüne koyar. Örnekler geldi; yapıları 2.3'te. |
| 20/10/2026 | Ana ekran ve pano (soru 28) | Ana ekran siparişler listesidir. Ayrıca aşama sütunlarından oluşan bir Pano ekranı olur; her ürün kendi aşamasının sütununda durur. Şimdilik ihtiyacı karşılıyor. |
| 20/10/2026 | Yazı tipi (soru 28) | Uygulama Inter yazı tipini kullanır. Yazı tipi dosyası uygulamanın içine konur, internet gerekmez. Boyut: soru 35. |
| 20/10/2026 | Depo bilgisi (soru 20) | Depo stok raporlarından anlaşılır; her depo ayrı dosyadır. ERP'de tamamlanan ürün montaj üretim deposunda görünür. Ürün sevk deposunda değilse uygulama "Testi yapıldı mı?" diye sorar (3.1). |
| 20/10/2026 | Toplu yükleme (soru 29) | Her sipariş için ayrı form yerine toplu listeler yüklenir: açık ve tamamlanan sipariş talepleri, açık ve kapalı iş emirleri, çıkış yapılamayan malzeme raporu, stok raporları. Yükleme her sabah ya da istenen an yapılır. |
| 20/10/2026 | Beklemede siparişler (soru 30) | ERP'de "Beklemede" olan sipariş satırları uygulamada soluk renkte, "onay bekliyor" diye görünür. Önemsiz ya da yanlış bir değer olduğu anlaşılırsa kullanıcı bildirecek. |
| 20/10/2026 | ERP ürün durumu (soru 31) | ERP'deki "Ürün Durumu"nu planlama birimi elle güncelliyor. Kartta "Planlama birimi ürün üretim durumu: …" diye gösterilir; yanında daha küçük yazıyla verinin hangi tarihte alındığı yazar. Uygulamanın kendi aşamasını değiştirmez. |
| 20/10/2026 | Kapalı iş emirleri (soru 32) | Kapalı iş emirleri listesi alınabiliyor; örneği geldi (2.3). |
| 20/10/2026 | Eksik miktar (soru 33) | Eksik = planlanan takip miktarı − gerçekleşen çıkış miktarı. |
| 20/10/2026 | Kart olan satırlar (soru 34) | SVR, OVR, OVF, WD, PP, SCN, KCN ve CB satırları kart olur; sonu "-MNT" ile bitenler servis kartı olur. OZ malzemeleri, hortum setleri, CP kitleri ve projeye özel ürünler (bağlantı çatalı, uzatma bomu…) sipariş kartında listelenir. İleride güncellenebilir; kural Ayarlar'dan değişir. |
| 20/10/2026 | Yazı boyutu (soru 35) | Yazılar çok küçük olmaz; telefonda ve atölyede rahat okunur. |
| 21/10/2026 | Planner'dan geçiş (soru 13) | Planner, uygulamaya tam geçilene kadar kullanılmaya devam eder; geçilince tamamen bırakılır. Kartlar ERP listelerinden oluşur. Planner Excel'i iki iş için kullanılır: açık kartların notlarındaki bilgiler (çene no, şanzıman no, motor seri no…) ERP'de eşleşen kartların boş alanlarına doldurulur; tamamlanmış kartlar değiştirilemeyen, aranabilir bir "Planner arşivi" olarak alınır. |
| 21/10/2026 | Planner özeti (2. bölüm) | Kullanıcı onayladı; denemelerde aksi söylenmedikçe geçerli. |
| 21/10/2026 | Kişi atama (soru 36) | Kartlara kişi atanır; "bana atananlar" süzgeci olur. Ürün ailesine göre varsayılan atama: vibrohammer, çene, kiriş ve bunların yarı mamulleri montaj ekibindeki iki kişiye; PP ve yarı mamulleri kullanıcıya (ekip lideri). Genel müdür ve montaj fabrikası müdürü kartlara atanmaz, ama her şeyi görür. Adlar git'e girmez; `OMS Veri/kurulum/atama-ve-roller.txt` dosyasında. Kalanlar: soru 40. |
| 21/10/2026 | Öncelik (soru 37) | Öncelik alanı olmaz; aciliyet "Sıcak sipariş" etiketiyle gösterilir. |
| 21/10/2026 | Görünümler (soru 38) | İlk sürümde siparişler listesi ve pano olur. Takvim ve grafikler sonraki sürüme kalır. |
| 21/10/2026 | Çalışma yeri (soru 39) | Eski portal gibi şirket sunucusunda çalışan, tarayıcıdan açılan bir web sitesi olur (adresi 192.168 ile başlar). Şirket ağına bağlıyken bilgisayardan ve telefondan açılır. Kullanıcıya telefonda açacağı bir bağlantı verilir. Kurulum ayrıntıları: soru 41. |
| 21/10/2026 | Atamanın kalanı (soru 40) | OVF, WD, servis ve yedek parça kartları da montaj ekibindeki iki kişiye atanır. |
| 21/10/2026 | Müdürler izleyicidir (soru 40) | Genel müdür ve fabrika müdürü her şeyi görür ama değiştiremez (7b'deki "yetki ayrımı yok" kararının istisnası). Hata görürlerse (yanlış iş emri, eksik ürün…) kartta "Atanan kişiye hata bildir" düğmesiyle atanan kişiye WhatsApp'tan mesaj gönderebilirler. Hazır mesaj örneği: "<sipariş no> siparişinde bulunan <ürün kodu> kartında hata ile karşılaştım, ilgilenir misin?" Gönderim yolu: soru 42. |
| 21/10/2026 | Sunucu kurulumu (soru 41) | Uygulama eski portalla aynı şirket sunucusunda, ayrı bir adreste çalışır. Eski portal Docker ile çalışıyor; yenisi de öyle kurulur. Kurulumu kullanıcı yapar; IT de ilgileniyor. Telefonlar şirket Wi-Fi'ına bağlanabiliyor. |
| 21/10/2026 | Siparişler listesinin düzeni | Açık siparişler üç teslim sütununda dizilir: Gecikenler, 14 gün içinde, Planlananlar (kullanıcı "Daha sonra" yerine bu adı seçti); en sağda dördüncü sütun "Onay bekleyen projeler". Her sütunda kutular teslim tarihine göre yukarıdan aşağı. Kutudaki ürün kutucukları (1 PP, 1 SVR…) tıklanınca siparişin o ürün ailesinin bölümüne gider; 3. adımda ürünün iş emri ve durumuna gidecek. |
| 21/10/2026 | Onay bekleyenler sevk edilecek sayılmaz | Onay bekleyen sipariş kesin olmadığından sevk edilecek ürünlere, pastalara, haftalık takvime, açık sipariş ve teslim (geçen, 14 gün içinde) sayılarına girmez. Siparişler ekranında teslim sütunlarında değil, en sağdaki "Onay bekleyen projeler" sütununda soluk görünür; Özet'te kendi "Onay bekleyen" kutusunda sayılır. Bir siparişin yalnızca bazı satırları onay bekliyorsa sipariş açık sayılır, teslim tarihi onaylı satırlardan alınır. |
| 21/10/2026 | Sipariş talebi revizyonları | Sipariş taleplerinde açıklama ya da ürün revizyonları oluyor. Her yüklemede daha önce bilinen siparişlerin değişiklikleri kaydedilir: ürün kodu, ürün adı, miktar, açıklama (renk, yağ), teslim tarihi, seri no, sipariş notu, yeni eklenen ve iptal edilen satırlar. Sipariş kartında "Sipariş talebi revizyonları" tablosu (yükleme tarihi, satır, ne değişti, önce, sonra) ve değişen satırda "Revize edildi" etiketi görünür; Siparişler ekranında kutuda "Revize" etiketi 30 gün durur. Yüklenen dosyada hiç dolu olmayan sütun karşılaştırılmaz (rapora alınmamış olabilir). Kayıt bu sürümden sonraki ilk yüklemeyle başlar. |
| 21/10/2026 | Seri no'suz OVF ve WD satırları | OVF ve WD siparişlerinde seri no'su olmayan satırlar makine değil, makinenin parçasıdır (örnek: OVF-300-BF-LM-B, OVF-300-4BF-BSP'nin parçası). Makine sayılarına, pastalara ve sevkiyata girmez, ürün kartı açılmaz; sipariş kartında "Aksesuarlar ve diğer kalemler" listesinde görünür. SVR, OVR ve PP satırlarının hepsinde seri no var; kural yalnızca OVF ve WD için. |
| 21/10/2026 | Listede görünmeyen sipariş satırı | Satır numarası atlanan siparişte kartta uyarı kalır: OZ-… örneğinde PDF'teki bir satır (bağlantı çatalı) ERP listesinde yoktu, büyük olasılıkla ERP'de silinmişti; uyarı bu farkı yakaladı. Liste iptal edilen satırları da getirdiği için görünmeyen satır çoğunlukla silinmiş satırdır. 4. adımda uyarının yanına "Kontrol ettim, satır silinmiş" düğmesi eklenir; işaretlenen siparişte uyarı görünmez. |
| 21/10/2026 | İş emirlerinin siparişe bağlanması (3a) | Açık ve kapalı iş emirleri listeleri yüklenir (ikisi aynı rapor biçiminde; "Durumu" Açık ya da Kapalı). Bağlantı her yüklemeden sonra baştan kurulur, sırayla: (1) ERP bağlantısı: sipariş satırının "Bağlı İşemri No"su ya da iş emrinin "Sip. No"su ("…-<proje>-<sıra>-" biçiminde, sipariş satırını gösterir; 20/10 örneğinde ikisi hep aynı iş emrini gösteriyor); (2) iş emri açıklamasındaki proje kodu ve siparişte aynı ürün; (3) proje kodu var ama ürün siparişte yok: alt montaj ya da yarı mamul, sipariş kartında ayrı tabloda; (4) açıklamada "stok": stok için; (5) hiçbiri: bağlanamadı, kullanıcıya sorulur (3a'nın ikinci yarısı). Siparişe bağlı iş emri, satırın ürün kartlarına adet sırasıyla dağıtılır; ürün "Sipariş" aşamasındaysa "Malzeme hazırlık"a geçer. Üretim girişi olmadan kapatılan iş emri ürüne dağıtılmaz, kartta öyle yazar. Açık bir iş emrinin bitmiş kırılımları kapalı listede olabiliyor (20/10 örneğinde 8 iş emri); kırılımlar iki listeden birleştirilir. |
| 23/10/2026 | Ürün sayfası (3b öne alındı) | Ürüne tıklayınca yalnızca o makinenin sayfası açılır: sipariş kutusundaki ürün kutucuğu (siparişte o aileden tek makine varsa; birden çoksa siparişin o bölümü açılır, oradan her makine kendi sayfasına gider), sevk edilecek makineler listesi ve sipariş kartındaki ürün. Sayfada makinenin bilgileri, numaraları, iş emri ve kırılımları (tamamlanan ve bekleyen, ilerleme çubuğuyla) görünür. Siparişe tıklayınca bütün kalemleriyle sipariş kartı açılır. |
| 23/10/2026 | Motor seri no ve şasi no | Motor seri no'su takibin en önemli bilgilerindendir. ERP iş emri açıklamalarında etiketsiz yazılıyor ("<proje> - 0000 111 101 - …" Volvo, "<proje> / N5F00001 / …" CAT; bir yıllık listede 120 Volvo, 42 CAT biçiminde). Uygulama güç ünitesinin motor seri no'sunu kendi iş emrinin ve kırılımlarının açıklamasından, orada yoksa ve siparişte tek güç ünitesi varsa projenin motor-pompa hattı iş emrinden okur (alt montaj tablosunda ayrı motor seri no sütunu gerekmedi, kaldırıldı). Vibrohammerın şasi no'su ERP'de yok; Planner notlarında "Şasi No" ve "Şanzıman (Seri) No" olarak tutuluyordu. Numaralar ürün sayfasından elle girilir; ekibin girdiği ERP'den okunanın önüne geçer, silinince ERP'den okunan yeniden görünür. Toplu giriş için "Makine numaraları" şablonu: ERP yükleme ekranından indirilir (bütün makineler hazır gelir), şasi ve motor seri no'ları doldurulup aynı ekrandan yüklenir; boş hücre değiştirilmez, satır Kart No ile eşleşir. Hangi makinede hangi alan: SVR, OVR şasi no; PP motor seri no; OVF, WD ikisi de (denemelerde netleşir). |
| 23/10/2026 | Motor seri no biçimleri | Volvo motor seri no'ları çoğunlukla 4+3+4 rakam ("0000 111 1011" biçiminde; bir yıllık listede 421'e 120), daha az 4+3+3 yazılıyor; ikisi de okunur. Sipariş kartında motor seri no (vibrohammerda şasi no) seri no gibi her zaman yazar, yoksa "yok" görünür. Sevk edilecek makineler listesinde "Şasi / motor no" sütunu ve makinenin bağlı iş emri durumu görünür. OVF ve WD'de şasi no yok; numara alanı ve şablon satırı yalnızca SVR, OVR (şasi no) ve PP (motor seri no) için. |
| 23/10/2026 | ERP'nin iş emri kapanış notu | ERP iş emrini kapatınca açıklamanın sonuna "<sıra no> NOLU İŞEMRİNİN PLAN MİKTAR <= GERÇEKLEŞEN MIKTAR DURUMUNDAN DOLAYI ZAMANLANMIS GOREV TARAFINDAN KAPATILDI." ekliyor; sıra numarası önceki kelimeye (bazen motor seri no'suna) yapışıyor, iş emri birden çok kez kapandıysa not tekrar ediyor. Uygulama notu okurken sıra numarasıyla birlikte siler; açıklamada görünmez, motor seri no doğru okunur. |
| 23/10/2026 | İş emri durum renkleri | İş emri kutusu ve sipariş kartında ürünün solundaki şerit: iş emri tamamlandı açık yeşil ("ERP'de iş emri tamamlandı"), açık ya da kısmen tamamlandı sarı, iş emri açılmadı (açılacak) soluk kırmızı, sevk edildi gri. |
| 23/10/2026 | Siparişin durumu özeti | Sipariş kartının ve ürün sayfasının başında küçük bir "Siparişin durumu" kutusu: siparişteki ürünlerin kaçının iş emri tamamlandı, kısmen tamamlandı, açık, açılmadı, sevk edildi; PP'ye takılacak kalemlerin montaj durumları. Her durum tıklanır: sipariş kartı yalnızca o durumdaki kalemlerle açılır ("bütün kalemleri göster" ile geri dönülür). |
| 23/10/2026 | PP'ye takılan kalemler | Kablosuz kumanda seti (OZ04314) ve uzaktan erişim modülü (OZ04082) dışarıdan alınıp güç ünitesine takılıyor. Makine siparişinde bu satırların yanında montaj durumu seçilir: sipariş talebi açılacak (soluk kırmızı), sipariş talebi açıldı, bekleniyor (sarı), geldi, montaj edilmedi (mavi), PP'ye montaj edildi (yeşil). Ekip seçer, izleyici görür; ERP yüklemesi değiştirmez. Güç ünitesinin sayfasında da listelenir. Kod listesi 6. adımda Ayarlar'a taşınır. |
| 23/10/2026 | ERP'den canlı veri | ERP sorumlusu ERP'den canlı veri çekilebileceğini söyledi. Uygulama buna hazır kuruldu (ERP okuyucu katmanı); Excel yüklemesinin yerine bağlantı ilerleyen günlerde eklenir. Gerekenler ERP sorumlusundan istenecek: bağlantı türü (veritabanına salt okunur kullanıcı ya da web servisi), raporların karşılığı olan görünümler, sunucudan erişim, yenileme sıklığı. Yeni bir kütüphane gerekebilir (eklemeden önce sorulur). ERP'ye yine hiçbir şey yazılmaz. Netleşenler: bağlantı ERP'nin bir arayüzüyle (büyük olasılıkla API) kurulacak; raporların hazır görünümlerinin tamamı verilebilir; veri 15 dakikada bir çekilebilir. Satın alma talebi açılan kalemlerin açıklamasına hangi sipariş için açıldığı yazılabiliyor; bu görünüm gelince PP'ye takılan kalemlerde "ERP'de … numaralı istekte siparişi var" bilgisi kendiliğinden gösterilir. |
| 23/10/2026 | Yapay zekâ asistanı (öneri) | Kullanıcı uygulamaya soru sorulabilen bir asistan istiyor ("OZ-… siparişinin özeti, motor seri no, montaj bitti mi?"). Öneri: Claude API ile, asistanın yalnızca uygulamanın kendi sorgularını araç olarak kullanması (cevap veritabanından gelir). 5 kişi, az soru için aylık maliyet birkaç dolar ile birkaç on dolar arası (model seçimine göre). Gerekenler: sunucunun internete çıkışı, şirket adına API hesabı ve anahtarı, sipariş bilgisinin dış servise gitmesi için IT/yönetim onayı, `anthropic` kütüphanesi (onayla). Plan sonrasına (8. adımdan sonra) eklenir. |
| 23/10/2026 | Yapay zekâ asistanı denemesi | Kullanıcı Claude Haiku 5.5 ile denemeyi istedi; `anthropic` kütüphanesi onaylandı ve eklendi. Deneme önce uydurma veriyle yapılır: `asistan-deneme.bat` ayrı bir veri klasöründe (`OMS Veri/asistan-deneme`) uydurma siparişlerle ayrı bir adreste (port 8091) açar, gerçek veritabanına dokunmaz. Asistan yalnızca okur; dört aracı var: sipariş arama, sipariş bilgisi, makine arama (seri, şasi, motor no), sevk edilecek makineler. Aynı konuşmadaki son 3 soru-cevabı hatırlar (devam soruları için), "Yeni konuşma" ile sıfırlanır. Her soru, cevabı ve yaklaşık maliyeti kaydedilir; sayfada her cevabın ve bu ayın toplam maliyeti görünür. Cevaptaki kalın yazı ve maddeler biçimli gösterilir. Deneme kopyası ayrı oturum çerezi kullanır; ana uygulamayla aynı anda açık olabilir. Asistan OMS_ASISTAN=1 ile açılır. API anahtarı `OMS Veri/anthropic-anahtar.txt` dosyasında durur, git'e girmez. |
| 23/10/2026 | Asistan: gerçek veri ve sohbet kutusu | Kullanıcı asistanı gerçek verilerle, ana uygulamada (baslat.bat) denemek istedi ve sipariş bilgilerinin cevap için Anthropic'e gitmesini onayladı; baslat.bat asistanı açar. Asistan ayrı sayfa değil, her ekranın sağ altındaki sohbet kutusudur; sayfa değişince konuşma ve kutunun açık olması korunur. Örnek sorular yok; kutu kullanıcıyı adıyla karşılar: "Merhaba <ad>, hoş geldiniz. Size nasıl yardımcı olabilirim, neyi öğrenmek istersiniz?" "Bey/Hanım" hitabı kendiliğinden eklenmez (kişinin hitabı bilinmiyor); istenirse kullanıcı ayarlarına hitap alanı eklenir. Uydurma verili deneme (asistan-deneme.bat) de kalır. |
| 23/10/2026 | Bağlanamayan iş emirleri (3a, ikinci yarı) | Yapılacaklar ekranı açıldı; ilk bölümü bağlanamayan iş emirleri: açık olanlar ve son 60 günde kapananlar. Ekip her biri için seçer: aynı ürünü bekleyen sipariş satırı (iş emri olmayan adet sayısıyla), başka bir sipariş (ürün siparişte yoksa alt montajı olarak), stok için açılmış ya da takip edilmeyecek. Seçim, kim ve ne zaman saklanır; ERP yüklemesi değiştirmez; "Elle bağlananlar"dan geri alınır. Menüde Yapılacaklar'ın yanında bekleyen sayısı görünür. Proje kodu iş emrinin ürün kodunda da aranır (OZ-<proje>-PR-01 gibi projeye özel ürünler kendiliğinden bağlanır); gerçek veride sorulacak sayı 63'ten 50'ye indi (20'si açık). |
| 23/10/2026 | İki motorlu güç üniteleri | Model numarası 1000 ve üstü güç üniteleri (PP-1072, PP-1102, PP-1536, PP-1592) iki motorludur (kullanıcı seçti). Ürün sayfasında, sipariş kartında, sevk edilecek makinelerde ve "Makine numaraları" şablonunda "Motor 1 seri no" ve "Motor 2 seri no" ayrı ayrı görünür ve girilir; iki numara "/" ile yan yana tek numara gibi yazılmaz. ERP'den okurken önce iş emrinin kendi açıklamasına, sonra kırılımlarına bakılır; gereken sayıda numara içeren ilk açıklama alınır (bir yıllık listede kırılımlar bazen başka bir güç ünitesinin motorunu da yazıyor). Gerçek veride 9 iki motorlu güç ünitesinin 7'sinde iki numara da okunuyor. İki motorlu güç ünitelerinin diğer ayrıntıları adımlar ilerledikçe eklenecek. |
| 23/10/2026 | Yapılacaklar süzgeci | Liste karmaşık olduğu için ürün ailesine göre süzülür: Tümü, SVR, OVR, PP, Çene, Kiriş, OVF, WD, Diğer (her birinin yanında sayısı; boş aileler soluk). Alt montaj ve yarı mamullerin ailesi ürün adından okunur ("OVR Blok Montaji", "PP Hortum Seti"). Bir aile seçilince iş emirleri bölümlere ayrılır: makinenin kendisi, alt montajlar adlarına göre (PP'de motor-pompa hattı, yağ tankı…) ve bakım-onarım. "Kaydet" sayfayı yenilemeden kaydeder; iş emrinin yerinde "Kaydedildi" yazar, liste yerinde kalır, sayılar azalır. Bugün PP iş emirlerinin hepsi ERP'de projeye bağlı olduğundan PP'de soru yok; PP'nin bölümleri eksik malzeme (3c) gelince dolar. |
| 23/10/2026 | Eksik malzeme (3c) | "Çıkış yapılamayan malzeme" raporu yüklenir (her yüklemede baştan yazılır; ERP'nin bugünkü hâli). Planlanan takip miktarı gerçekleşen çıkıştan büyükse malzeme eksiktir. Ürün sayfasında eksikler kırılım kırılım listelenir (kırılım tablosunda da sayısı görünür); sipariş kartında iş emrinin yanında "12 malzeme eksik". Depoda olan malzeme sarı ("depoda var, çıkışı yapılmamış", hangi depoda kaç tane), olmayan kırmızı; ikisi de sorulur (kullanıcı seçti). Yapılacaklar'da iş emri başına tek soru: "Bilginiz var mı?" Cevaplar: Biliyorum, bekleniyor · Montajı etkilemiyor · Depoya / satın almaya bildirdim · ERP'de hata var. Cevaptan sonra yeni bir malzeme eksik görünürse ya da eksik miktarı artarsa yeniden sorulur; "takip etme" denen iş emri sorulmaz. 23/10 raporunda 53 iş emrinde 752 eksik (345'i depoda var); bir iş emri iş emri listesinde olmadığı için 52 soru. Birlikte yüklenen listeler sırayla işlenir: siparişler, iş emirleri, eksik malzeme. |
| 23/10/2026 | "İmalatta" uyarısı (3c) | İş emri stoğa girmeye başlamış (kısmen ya da tamamen) ama planlama biriminin ERP ürün durumu hâlâ "İmalatta" ise ürün sayfasında, sipariş kartında ve Yapılacaklar'da uyarı: "… Emin misiniz?" Ekip planlamaya bildiremediği için "planlamaya bildirdim" seçeneği yok; aynı üründen birden çok olsa da her ürün ve iş emri için ayrı sorulur (kullanıcı). Cevaplar: "Ürün montajda ya da tamamlandı; ERP güncel değil" ve "ERP doğru, ürün imalatta"; cevap kartta görünür. ERP'deki durum değişince uyarı kendiliğinden kalkar. 23/10 verisinde 7 ürün. |
| 23/10/2026 | Yapılacaklar konuları | Yapılacaklar'da üç konu var: eksik malzeme, ERP'de "İmalatta", bağlanamayan iş emri. Konu ve aile süzgeçleri birlikte kullanılır; her süzgecin yanında sayısı görünür. Menüdeki sayı üçünün toplamıdır. |
| 23/10/2026 | Sipariş kutusunda ürün kodu | Siparişler ekranındaki ürün kutucukları aile kısaltması (PP, SVR) yerine tam ürün koduyla yazılır: PP-536-NF, SVR-50-NF-BSP (kullanıcı tam kodu seçti). Özetteki sipariş tablosu tek ekrana sığsın diye aile kısaltmasıyla kalır. |
| 23/10/2026 | Asistan simgesi ve açılışı | Sağ alttaki düğmede kullanıcının hazırladığı OMS asistan simgesi var: `OMS Veri/uygulama/marka/ai-logo/oms-ai-ikon.svg` (kendi canlandırmasıyla; üzerine gelince titrer, gözleri kırpar). Canlandırma çalışsın diye resim olarak değil sayfanın içine gömülür; düğmenin zemini ve kenarlığı yoktur. Boyut 128×128 (kullanıcı 64'ü küçük buldu; telefonda ekranı kapatmasın diye 88). Üzerine gelince solunda "Montaj Asistanı" yazısı simgenin arkasından sola doğru kayarak çıkar; tıklayınca sohbet kutusu açılır. Dosya yoksa uygulamanın kendi simgesi görünür; betik içeren dosya gömülmez. Sohbet kutusu düğmeden büyüyerek açılır, kapanırken küçülür. İleride OMS için bir avatar düşünülebilir. Kullanıcı Anthropic'in iade cevabını beklediği için şimdilik soru sormuyor; kutu duruyor. |
| 21/10/2026 | İş emri tamamlandı ama ERP "İmalatta" (3. adım) | İmalat fabrikası başka yerleşkede; planlama biriminin ERP'deki "Ürün Durumu" geç güncellenebiliyor (örnek: montajına başlanan üç sipariş ERP'de hâlâ "İmalatta"). Siparişteki bir ürünün iş emri tamamlanmaya başlamışsa (stok girişi kısmen ya da tamamen yapılmışsa) ama ERP ürün durumu hâlâ "İmalatta" ise uygulama ürünün kartında ve Yapılacaklar'da uyarır: "İş emri tamamlanmış, stok oluşmuş görünüyor; ERP'de ise İmalatta görünüyor. Emin misiniz?" İş emirleri yüklemesiyle (3. adım) gelir; cevap seçenekleri o adımda netleşir. |
| 21/10/2026 | Özet sayfası | Ana ekran Özet'tir; girişte ilk o açılır. Ana portalın "Bilgilendirme" panosundan uyarlandı: açık sipariş, sevk edilecek ürün, teslimi geçen, 14 gün içinde teslim ve onay bekleyen sayıları; ürün ailelerine ve planlama birimi durumuna göre dağılım; haftalık teslim takvimi; teslimi geçen ve yaklaşan siparişler tablosu. Grafikler uygulamanın içinde çizilir, yeni bağımlılık yok. |
| 21/10/2026 | Özet sayfası düzeltmeleri | Bilgisayarda kaydırmadan tek ekrana sığar. Bütün sayı kutuları tıklanır. Ürün aileleri ve planlama durumu pasta (halka) grafiktir; her aile her grafikte aynı renktir (renk sırası halka olarak renk körlüğü denetiminden geçti). Haftalık takvim dardır. |
| 21/10/2026 | Sevk edildi (çeyrek dönem) | Özette "Sevk edildi" kutusu bu çeyrekte sevk edilen ürün ve sipariş sayısını gösterir; her çeyrek başında sıfırdan başlar. Kayıtlar silinmez: Sevkiyat sayfasında çeyrek seçilerek geçmiş dönemler incelenir (aileye göre dağılım ve sevk edilen siparişler). Sevk tarihi şimdilik ERP'deki son sevk tarihidir. |
| 21/10/2026 | Ürüne tıklayınca açılan sayfa (3. ve 4. adım) | Sipariş kutusundaki ürüne (PP, SVR…) tıklanınca sipariş kalemleri değil, ürünün kendi sayfası açılır: o ürün için açılan iş emri ve durumu (tamamlandı, imalatta, malzeme bekliyor, montaj alanında…). PP gibi ürünlerin iş emrinde 10 civarı kırılım (alt montaj) var; hangileri tamamlandı, hangileri bekliyor görünür. Kırılımlar tamamlanıp ürün oluşunca sıradaki iş görünür; önerilen sıra: test → motor açılışı → motor eksperi → metal etiket yapıştırıldı mı? |
| 21/10/2026 | Özette ve sevkiyatta sayılan ürünler | Pastalar ve sayılar yalnızca makineleri sayar: SVR, OVR, PP, OVF, WD. Çene ve kiriş bunlara girmez (pastayı fazla dolduruyordu); kartlarda ve listelerde görünmeye devam eder. |
| 21/10/2026 | Haftalık takvim | Sütuna tıklayınca "Sevk edilecek makineler" sayfası, teslimi o haftada olan makinelerle açılır ("Geciken" sütunu teslimi geçmiş olanlarla). |
| 21/10/2026 | Sevk edilecek makineler sayfası | Özetteki "Sevk edilecek ürün" kutusu, aile pastası, planlama birimi pastası (İmalatta, Montajda, Hazır, Sevke Hazır, Belirtilmemiş) ve haftalık takvim aynı sayfayı açar: sevk edilecek makineler proje proje gruplanır; her makinenin ürün kodu, seri no, aşaması, planlama durumu, iş emri ve teslim tarihi görünür. Sayfanın üstünde planlama durumuna göre seçim yapılır. Satıra tıklayınca sipariş kartı açılır. Özetteki sayılar bu sayfayla aynı hesaptan gelir. |
| 21/10/2026 | Özet başlıkları | Özetteki kart başlıkları büyük harfle yazılır; pastaların ortasındaki "MAKİNE" yazısı büyük harfli ve daha iri; "dilime tıklayın" notu yok. |
| 21/10/2026 | Logo filigranı | Özette "Açık sipariş" ve "Sevk edilecek ürün" kutularının üzerine gelince arkada OMS logosu şeffaf görünür. |
| 21/10/2026 | Müşteriye özel görünüm | Sipariş kutusunun üzerine gelince zemin müşterinin rengine döner, yazılar beyazlaşır, müşterinin logosu arkada beyaz ve yarı şeffaf görünür; sipariş kartının başında bu görünüm her zaman vardır. Tanımlı müşterisi olmayan bütün siparişlerde OMS logosu ve OMS kırmızısı kullanılır (kullanıcı seçti; önce koyu antrasit denendi). Müşteri kodu sipariş numarasının "OZ-"den sonraki üç karakteridir. Ayar git'e girmez: `OMS Veri/uygulama/marka/musteriler.txt` (her satır `KOD;#renk;logo-dosyasi.png`; logo adı yazılmazsa `musteri-KOD.png` aranır; `*;#renk` satırı diğer müşterilerin rengini değiştirir). Logonun zemini saydam olmalı. İlk müşterinin rengi RAL 5017 (trafik mavisi, ekranda yaklaşık #0e518d). |
| 21/10/2026 | Yedek parça ekranı | Yedek parça siparişleri menüdeki ayrı "Yedek parça" ekranında tablo olarak izlenir; Siparişler'de ve Özet'te görünmez (Siparişler'de tip süzgeciyle seçilebilir). Sevkiyat sayfasında yedek parça sevkiyatı ayrı, açılır bir bölümdedir. Hazırlanıyor ve sevke hazır aşamaları 4. adımda. |
| 21/10/2026 | ERP listesi gerçeği gösterir | En son yüklenen sipariş listesi ERP'nin bugünkü hâlidir. Açık görünüp bu listede bulunmayan siparişler açık siparişlerden çıkarılır (silinmez; "ERP listesinde yok" süzgeciyle görülür), listede yeniden görünürse geri gelir. Aynı sipariş satırı listede iki kez geçerse iptal edilmemiş kayıt geçerlidir. Süzgeçsiz liste (21/10/2026) bütün imalat türlerini içeriyor; satır boşlukları 151'den 20'ye indi. |
| 21/10/2026 | Yanlış girilip iptal edilen satırlar | ERP'de yanlış girilen satırlar "Yanlış" notuyla iptal edilip doğruları giriliyor; iptal kaydı listede kalıyor ve geçerli satırla aynı satır numarasını taşıyabiliyor. Aynı numaralı kayıtlardan iptal edilmemiş olan geçerlidir. Siparişin notu ve diğer bilgileri iptal satırlarından alınmaz. Devam eden siparişte iptal edilmiş satırlar ürünlerin arasında değil, kartın altındaki kapalı "İptal edilen satırlar" bölümünde, ERP açıklamasıyla görünür. Bir siparişte iptal kayıtları ile yeniden girilen doğru satırlar kısmen aynı satır numaralarını taşıyabiliyor (21/10/2026 incelemesi); bu yüzden düzeltme ancak liste yeni sürümle yeniden yüklenince ekrana yansır. |
| 21/10/2026 | Dış tedarik kalemleri | "OZ" + rakam kodlu kalemler (kablosuz kumanda, hortum, cıvata…) dış tedariktir: burada üretilmez, iş emri açılmaz. Sipariş kartında ERP "Ürün Durumu" yerine "Dış tedarik" yazar; yedek parça ekranının planlama durumu yalnızca burada üretilen parçalardan hesaplanır. "OZ-<proje>-PR-01" gibi projeye özel ürünler burada üretildiği (iş emri açıldığı) için dış tedarik sayılmaz. |
| 21/10/2026 | Renk ve tıklama | Ürün kutucukları pastadaki aile rengini taşır (renk zeminde, kenarda ve noktada; yazı koyu). Özet, Sevkiyat ve Yedek parça tablolarında satırın tamamı tıklanır. |
| 21/10/2026 | Görünüm | Ekranlar arası geçişte içerik hafifçe kayarak belirir (hareketi kapatmış kullanıcılarda yok). Menü sırası: Özet, Siparişler, Yedek parça, Pano, Stok, Yapılacaklar, Sevkiyat, ERP yükleme, Arşiv, Ayarlar. ERP yüklemede büyük, renkli, sürükle-bırak destekli dosya alanı. |
| 21/10/2026 | Uygulama planı | `docs/uygulama-plani.md` onaylandı; eksik görülmedi. Bağımlılıklar onaylandı: Flask, Waitress, openpyxl, xlrd, Pillow, Inter yazı tipi dosyaları, pytest (yalnızca geliştirmede). |
| 21/10/2026 | Telefondan deneme | Kullanıcının bilgisayarında Windows güvenlik duvarı dışarıdan gelen bağlantıları engelliyor; telefondan deneme şimdilik bekler, acelesi yok. Denemeler bilgisayarda yapılır (telefon görünümü için tarayıcıda F12, Ctrl+Shift+M). 2. adımdan sonra deneme sürümünün sunucuya erken kurulması düşünülebilir. |
| 21/10/2026 | Logo | Giriş ve kurulum ekranında şirket logosu, altında "MONTAJ" yazısı ve logonun ikiye bölünüp açıldığı canlandırma olur. Logo dosyası git'e girmez: `OMS Veri/uygulama/marka/oms-logo.png` (ya da .svg); PNG'nin boş kenarlarını uygulama kırpar. |
| 21/10/2026 | WhatsApp ile hata bildirimi (soru 42) | (a) WhatsApp bağlantısı: düğme WhatsApp'ı hazır mesajla açar, gönderen yalnızca "Gönder"e basar. Kurulum ve ücret yok; telefon numaraları uygulamaya bir kez girilir. Bildirim kartın zaman akışına yazılır ve atanan kişinin Yapılacaklar listesine düşer. |
| 21/10/2026 | Görev sohbetleri (soru 14) | Sohbetler otomatik aktarılmaz. Kullanıcı önemli notları (hepsini değil) elle gönderir; bunlar ilgili kartın zaman akışına girer. Gerçek veri olduklarından git'e girmez. |
| 20/10/2026 | Kartların kapanışı (bugün) | Kartlar, ürün sevk edilip irsaliyeli çıkış belgesi hazırlandıktan sonra elle kapatılıyor. Yeni sistemdeki kapanış: soru 9. |
